"""
DanTagGen Node - Generates Danbooru-style tags using KBlueLeaf's DanTagGen models.

Supports delta-rev2, delta, gamma, beta, alpha variants.
Delta models support an additional `quality` field in the prompt.
Models are cached globally to avoid reloading on each execution.
"""

from contextlib import nullcontext
from random import shuffle

import torch
from comfy.comfy_types.node_typing import IO, ComfyNodeABC, InputTypeDict
from transformers import LlamaForCausalLM, LlamaTokenizer


# =============================================================================
# CONSTANTS
# =============================================================================

MODELS = [
    "KBlueLeaf/DanTagGen-delta-rev2",
    "KBlueLeaf/DanTagGen-delta",
    "KBlueLeaf/DanTagGen-gamma",
    "KBlueLeaf/DanTagGen-beta",
    "KBlueLeaf/DanTagGen-alpha",
]

# Models that support the `quality` prompt field
DELTA_MODELS = {
    "KBlueLeaf/DanTagGen-delta-rev2",
    "KBlueLeaf/DanTagGen-delta",
}

QUALITY_TAGS = [
    "masterpiece",
    "best quality",
    "great quality",
    "good quality",
    "normal quality",
    "bad quality",
    "worst quality",
]

RATING_TAGS = [
    "safe",
    "sensitive",
    "nsfw",
    "nsfw, explicit",
]

TARGET_LENGTH = {
    "very_short": 10,
    "short":      20,
    "long":       40,
    "very_long":  60,
}

SPECIAL_TAGS_SET = {
    "1girl", "2girls", "3girls", "4girls", "5girls", "6+girls",
    "1boy",  "2boys",  "3boys",  "4boys",  "5boys",  "6+boys",
    "multiple girls", "multiple boys", "1other", "2others",
}

# Global model cache: { model_name: (tokenizer, model) }
_MODEL_CACHE: dict = {}


# =============================================================================
# MODEL MANAGEMENT
# =============================================================================

def get_model(model_name: str):
    """Load model from HuggingFace (or return cached instance)."""
    if model_name not in _MODEL_CACHE:
        import comfy.model_management as model_management

        print(f"[DanTagGen] Loading model: {model_name}")
        device = model_management.get_torch_device()

        tokenizer = LlamaTokenizer.from_pretrained(model_name)
        model = (
            LlamaForCausalLM.from_pretrained(model_name, attn_implementation="sdpa")
            .requires_grad_(False)
            .eval()
            .half()
            .to(device)
        )
        _MODEL_CACHE[model_name] = (tokenizer, model)
        print(f"[DanTagGen] Model ready on {device}")

    return _MODEL_CACHE[model_name]


# =============================================================================
# INFERENCE
# =============================================================================

@torch.no_grad()
def _generate(
    model,
    tokenizer,
    prompt:             str,
    temperature:        float = 1.35,
    top_p:              float = 0.95,
    top_k:              int   = 100,
    repetition_penalty: float = 1.17,
    max_new_tokens:     int   = 256,
) -> str:
    """Single generation pass. Decodes the full sequence to avoid token boundary artifacts."""
    import comfy.model_management as model_management
    device = model_management.get_torch_device()

    inputs         = tokenizer(prompt, return_tensors="pt")
    input_ids      = inputs["input_ids"].to(device)
    attention_mask = torch.ones_like(input_ids)

    autocast_ctx = (
        torch.autocast("cuda") if torch.cuda.is_available() else nullcontext()
    )

    with autocast_ctx:
        output = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repetition_penalty=repetition_penalty,
            max_new_tokens=max_new_tokens,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
            return_dict_in_generate=True,
            output_scores=True,
        )

    # Decode the full sequence (including prompt) to avoid mid-sequence token artifacts
    return tokenizer.decode(output.sequences[0])


def _tag_gen(
    model,
    tokenizer,
    prompt:         str,
    prompt_tags:    list[str],
    len_target:     int,
    black_list:     set[str],
    temperature:    float = 1.35,
    top_p:          float = 0.95,
    top_k:          int   = 100,
    max_new_tokens: int   = 256,
    max_retry:      int   = 5,
) -> tuple[str, list[str]]:
    """
    Iteratively generate tags until len_target is reached or retries are exhausted.

    Strategy:
      - Each pass uses the previous output as the next prompt (model continues from there).
      - Accumulate tags across passes — never discard previously generated tags.
      - If tag count stops increasing (stuck): reset to original prompt seeded with
        shuffled accumulated tags, up to max_retry times.
    """
    llm_gen:          str       = ""
    extra_tokens:     list[str] = []
    stuck_count:      int       = 0
    prev_extra_count: int       = -1
    original_prompt:  str       = prompt

    for _ in range(max_retry * 10):  # absolute hard cap
        llm_gen = _generate(
            model=model,
            tokenizer=tokenizer,
            prompt=prompt,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repetition_penalty=1.17,
            max_new_tokens=max_new_tokens,
        )

        llm_gen   = llm_gen.replace("</s>", "").replace("<s>", "")
        extra_raw = llm_gen.split("<|input_end|>")[-1].strip().strip(",")

        new_tokens = list(
            dict.fromkeys(
                tok.strip()
                for tok in extra_raw.split(",")
                if tok.strip() and tok.strip() not in black_list
            )
        )

        # Merge: keep existing accumulated tags, append only genuinely new ones
        seen = set(extra_tokens)
        for tok in new_tokens:
            if tok not in seen:
                extra_tokens.append(tok)
                seen.add(tok)

        # Rebuild llm_gen so the next prompt reflects all accumulated tags
        prefix  = llm_gen[: llm_gen.find("<|input_end|>") + len("<|input_end|>")]
        llm_gen = prefix + " " + ", ".join(extra_tokens)

        total = len(prompt_tags) + len(extra_tokens)
        print(f"  [DanTagGen] tags: {total} / {len_target}")

        if total >= len_target:
            break

        if len(extra_tokens) <= prev_extra_count:
            stuck_count += 1
            if stuck_count >= max_retry:
                print(f"  [DanTagGen] Stopping early: no progress after {max_retry} retries")
                break
            # Reset to original prompt seeded with shuffled accumulated tags
            shuffled = extra_tokens.copy()
            shuffle(shuffled)
            base   = original_prompt.split("<|input_end|>")[0]
            prompt = base + ", ".join(shuffled) + "<|input_end|>"
        else:
            stuck_count = 0
            prompt      = llm_gen.strip()

        prev_extra_count = len(extra_tokens)

    return llm_gen, extra_tokens


# =============================================================================
# PROMPT BUILDING & OUTPUT FORMATTING
# =============================================================================

def _build_prompt(
    is_delta:     bool,
    quality:      str,
    rating:       str,
    artist:       str,
    characters:   str,
    copyrights:   str,
    target:       str,
    special_tags: list[str],
    general:      str,
    aspect_ratio: float,
) -> str:
    general_part = ", ".join(special_tags)
    if general.strip():
        general_part += ", " + general.strip().strip(",")

    lines = []
    if is_delta:
        lines.append(f"quality: {quality or '<|empty|>'}")
    lines += [
        f"rating: {rating or '<|empty|>'}",
        f"artist: {artist.strip() or '<|empty|>'}",
        f"characters: {characters.strip() or '<|empty|>'}",
        f"copyrights: {copyrights.strip() or '<|empty|>'}",
        f"aspect ratio: {aspect_ratio:.1f}",
        f"target: <|{target}|>",
        f"general: {general_part}<|input_end|>",
    ]
    return "\n".join(lines)


def _format_output(
    special_tags: list[str],
    extra_tokens: list[str],
    general:      str,
    characters:   str,
    copyrights:   str,
    artist:       str,
    quality:      str,
    rating:       str,
    is_delta:     bool,
) -> str:
    all_general = (
        [t.strip() for t in general.strip().strip(",").split(",") if t.strip()]
        + extra_tokens
    )
    special = list(special_tags) + [t for t in all_general if t in SPECIAL_TAGS_SET]
    tags    = [t for t in all_general if t not in SPECIAL_TAGS_SET]

    chars = characters.strip().strip(",").replace("_", " ")
    copy_ = copyrights.strip().strip(",").replace("_", " ")
    art   = artist.strip().strip(",").replace("_", " ")

    out = ", ".join(special)

    if chars:
        out += f",\n\n{chars}"
        if copy_:
            out += f", {copy_}"
    elif copy_:
        out += f",\n\n{copy_}"

    if art:
        out += f",\n\nby {art}"

    quality_tag = quality if is_delta else "masterpiece"
    out += f",\n\n{', '.join(tags)},\n\n{quality_tag}, newest, absurdres, {rating}"

    return out


# =============================================================================
# COMFYUI NODE
# =============================================================================

class DanTagGen(ComfyNodeABC):
    """
    Generates Danbooru-style tags using KBlueLeaf's DanTagGen models.

    Outputs:
      - formatted_prompt: ready-to-use prompt string for CLIP Text Encode
      - raw_tags:         comma-separated extra tags generated by the model
    """

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                # ── Selects ──────────────────────────────────────────────
                "model_name": (MODELS, {"default": MODELS[0]}),
                "quality":    (QUALITY_TAGS, {"default": "masterpiece"}),
                "rating":     (RATING_TAGS,  {"default": "safe"}),
                "target":     (
                    ["very_short", "short", "long", "very_long"],
                    {"default": "long"},
                ),

                # ── Text boxes ───────────────────────────────────────────
                # special_tags: comma-separated, e.g. "1girl, solo"
                "special_tags": (
                    IO.STRING,
                    {
                        "default":   "1girl",
                        "multiline": False,
                        "tooltip":   "Comma-separated character count tags, e.g. '1girl, solo'",
                    },
                ),
                # general: seed tags for the model, comma-separated
                "general": (
                    IO.STRING,
                    {
                        "default":   "",
                        "multiline": True,
                        "tooltip":   "Seed tags passed to the model, e.g. 'dragon girl, dragon horns'",
                    },
                ),
                "artist": (
                    IO.STRING,
                    {"default": "", "multiline": False},
                ),
                "characters": (
                    IO.STRING,
                    {"default": "", "multiline": False},
                ),
                "copyrights": (
                    IO.STRING,
                    {"default": "", "multiline": False},
                ),
                # blacklist: comma-separated tags to exclude from output
                "blacklist": (
                    IO.STRING,
                    {
                        "default":   "",
                        "multiline": True,
                        "tooltip":   "Comma-separated tags to exclude from generated output",
                    },
                ),

                # ── Primitives ───────────────────────────────────────────
                "seed":        (IO.INT,   {"default": -1, "min": -1, "max": 2147483647, "step": 1}),
                "width":       (IO.INT,   {"default": 1024, "min": 64, "max": 8192, "step": 64}),
                "height":      (IO.INT,   {"default": 1024, "min": 64, "max": 8192, "step": 64}),
                "temperature": (IO.FLOAT, {"default": 1.35, "min": 0.1, "max": 2.0,  "step": 0.05}),
                "top_p":       (IO.FLOAT, {"default": 0.95, "min": 0.0, "max": 1.0,  "step": 0.01}),
                "top_k":       (IO.INT,   {"default": 100,  "min": 1,   "max": 500,  "step": 1}),
                "max_new_tokens": (IO.INT, {"default": 256, "min": 32,  "max": 1024, "step": 32}),
                "max_retry":   (IO.INT,   {"default": 5,   "min": 1,   "max": 20,   "step": 1}),
            }
        }

    RETURN_TYPES  = (IO.STRING, IO.STRING)
    RETURN_NAMES  = ("formatted_prompt", "raw_tags")

    FUNCTION  = "generate"
    CATEGORY  = "conditioning/utils"

    # -------------------------------------------------------------------------

    def generate(
        self,
        model_name:     str,
        quality:        str,
        rating:         str,
        target:         str,
        special_tags:   str,
        general:        str,
        artist:         str,
        characters:     str,
        copyrights:     str,
        blacklist:      str,
        seed:           int,
        width:          int,
        height:         int,
        temperature:    float,
        top_p:          float,
        top_k:          int,
        max_new_tokens: int,
        max_retry:      int,
    ) -> tuple[str, str]:

        # ── Set random seed for reproducibility ──────────────────────────
        if seed != -1:
            torch.manual_seed(seed)
        
        # ── Parse & validate text-box inputs ─────────────────────────────
        parsed_special = self._parse_tags(special_tags, field_name="special_tags")
        parsed_general = general.strip()
        parsed_black   = set(self._parse_tags(blacklist, field_name="blacklist", allow_empty=True))

        if not parsed_special:
            raise ValueError(
                "[DanTagGen] 'special_tags' must not be empty. "
                "Provide at least one tag, e.g. '1girl'."
            )

        # ── Derived values ────────────────────────────────────────────────
        is_delta     = model_name in DELTA_MODELS
        aspect_ratio = width / height
        len_target   = TARGET_LENGTH[target]

        prompt_tags = parsed_special + [
            t.strip() for t in parsed_general.strip(",").split(",") if t.strip()
        ]

        # ── Build prompt ──────────────────────────────────────────────────
        prompt = _build_prompt(
            is_delta=is_delta,
            quality=quality,
            rating=rating,
            artist=artist,
            characters=characters,
            copyrights=copyrights,
            target=target,
            special_tags=parsed_special,
            general=parsed_general,
            aspect_ratio=aspect_ratio,
        )

        print(f"[DanTagGen] Prompt:\n{prompt}")

        # ── Load model (cached) ───────────────────────────────────────────
        tokenizer, model = get_model(model_name)

        # ── Generate ──────────────────────────────────────────────────────
        _, extra_tokens = _tag_gen(
            model=model,
            tokenizer=tokenizer,
            prompt=prompt,
            prompt_tags=prompt_tags,
            len_target=len_target,
            black_list=parsed_black,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_new_tokens=max_new_tokens,
            max_retry=max_retry,
        )

        # ── Format outputs ────────────────────────────────────────────────
        formatted = _format_output(
            special_tags=parsed_special,
            extra_tokens=extra_tokens,
            general=parsed_general,
            characters=characters,
            copyrights=copyrights,
            artist=artist,
            quality=quality,
            rating=rating,
            is_delta=is_delta,
        )
        raw_tags = ", ".join(extra_tokens)

        return (formatted, raw_tags)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _parse_tags(
        value:       str,
        field_name:  str,
        allow_empty: bool = False,
    ) -> list[str]:
        """
        Parse a comma-separated tag string into a list of stripped tag strings.

        Raises ValueError with a clear message if an entry is malformed.
        """
        if not value.strip():
            if allow_empty:
                return []
            raise ValueError(
                f"[DanTagGen] '{field_name}' is empty. "
                f"Provide at least one comma-separated tag."
            )

        result = []
        for raw in value.split(","):
            tag = raw.strip()
            if not tag:
                # Tolerate trailing commas / double commas
                continue
            # Reject entries that look suspiciously non-tag-like
            # (newlines inside a single tag indicate a paste/formatting error)
            if "\n" in tag:
                raise ValueError(
                    f"[DanTagGen] '{field_name}' contains a newline inside a tag: {repr(tag)}. "
                    f"Separate tags with commas only, not newlines."
                )
            result.append(tag)

        return result