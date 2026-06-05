"""
SwitchSaveImage Node - A standard Save Image node controlled by a boolean switch.

When switch is ON: operates exactly like the standard Save Image node.
When switch is OFF: bypasses the save operation completely.
"""

from nodes import SaveImage

class SwitchSaveImage(SaveImage):
    """
    Save Image node with a built-in toggle.
    Inherits from core SaveImage to retain all standard functionality (naming, metadata, UI preview).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", ),
                "switch": ("BOOLEAN", {"default": True}),
                "filename_prefix": ("STRING", {"default": "ComfyUI"})
            },
            "hidden": {
                "prompt": "PROMPT", 
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    FUNCTION = "save_images_switch"
    CATEGORY = "utils"

    def save_images_switch(self, images, switch, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None):
        """
        Intercepts the save execution. 
        If switch is True, calls the parent's standard save logic.
        If False, returns an empty dict (no UI update, no file saved).
        """
        if not switch:
            return {}
        
        super().save_images(
            images=images, 
            filename_prefix=filename_prefix, 
            prompt=prompt, 
            extra_pnginfo=extra_pnginfo
        )

        return {}