"""
CLIPTextEncodeCombinedAnima Node - A QoL node that encodes both positive and negative 
prompts using a single CLIP model input, outputting two conditionings for Anima.
"""

from comfy.comfy_types.node_typing import IO

class CLIPTextEncodeCombinedAnima:
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
        positive_conditioning = clip.encode_from_tokens_scheduled(tokens_pos)

        tokens_neg = clip.tokenize(negative)
        negative_conditioning = clip.encode_from_tokens_scheduled(tokens_neg)

        return (positive_conditioning, negative_conditioning)