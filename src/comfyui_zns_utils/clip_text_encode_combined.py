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
                # Mặc định là widget text (có thể chuột phải -> Convert Widget to Input để cắm dây xám)
                "positive": ("STRING", {"multiline": True, "default": ""}),
                "negative": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    # Xuất ra 2 cổng CONDITIONING
    RETURN_TYPES = ("CONDITIONING", "CONDITIONING")
    
    # Đặt tên cho 2 cổng xuất để dễ nhìn trên UI (Cam)
    RETURN_NAMES = ("POSITIVE", "NEGATIVE")
    
    FUNCTION = "encode_combined"
    CATEGORY = "conditioning"

    def encode_combined(self, clip, positive, negative):
        # 1. Xử lý Positive Prompt
        tokens_pos = clip.tokenize(positive)
        cond_pos, pooled_pos = clip.encode_from_tokens(tokens_pos, return_pooled=True)
        # Đóng gói chuẩn format CONDITIONING của ComfyUI
        positive_conditioning = [[cond_pos, {"pooled_output": pooled_pos}]]

        # 2. Xử lý Negative Prompt
        tokens_neg = clip.tokenize(negative)
        cond_neg, pooled_neg = clip.encode_from_tokens(tokens_neg, return_pooled=True)
        # Đóng gói chuẩn format CONDITIONING của ComfyUI
        negative_conditioning = [[cond_neg, {"pooled_output": pooled_neg}]]

        # Trả về theo đúng thứ tự đã khai báo ở RETURN_TYPES
        return (positive_conditioning, negative_conditioning)