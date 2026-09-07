"""
CLIPTextEncodeCombined Node - A QoL node that encodes both positive and negative 
prompts using a single CLIP model input, outputting two conditionings.
"""

from comfy.comfy_types.node_typing import IO

class CLIPTextEncodeCombined:
    """
    Takes one CLIP model and two text inputs (positive/negative), 
    returns two separate CONDITIONING outputs.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": (IO.CLIP, ),
                "positive": ("STRING", {"multiline": True, "default": ""}),
                "negative": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING")
    
    RETURN_NAMES = ("POSITIVE", "NEGATIVE")
    
    FUNCTION = "encode_combined"
    CATEGORY = "conditioning"

    def encode_combined(self, clip, positive, negative):
        tokens_pos = clip.tokenize(positive)
        cond_pos, pooled_pos = clip.encode_from_tokens(tokens_pos, return_pooled=True)
        positive_conditioning = [[cond_pos, {"pooled_output": pooled_pos}]]

        tokens_neg = clip.tokenize(negative)
        cond_neg, pooled_neg = clip.encode_from_tokens(tokens_neg, return_pooled=True)
        negative_conditioning = [[cond_neg, {"pooled_output": pooled_neg}]]

        return (positive_conditioning, negative_conditioning)