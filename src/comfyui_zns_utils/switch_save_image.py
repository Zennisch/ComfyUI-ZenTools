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
                # Add the boolean switch widget directly to the node
                "switch": ("BOOLEAN", {"default": True}),
                "filename_prefix": ("STRING", {"default": "ComfyUI"})
            },
            # Hidden inputs are required to pass workflow metadata into the saved PNG
            "hidden": {
                "prompt": "PROMPT", 
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    # SaveImage core node has RETURN_TYPES = () and OUTPUT_NODE = True implicitly by its nature
    
    FUNCTION = "save_images_switch"
    CATEGORY = "utils"

    def save_images_switch(self, images, switch, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None):
        """
        Intercepts the save execution. 
        If switch is True, calls the parent's standard save logic.
        If False, returns an empty dict (no UI update, no file saved).
        """
        if not switch:
            # Return empty dictionary to ComfyUI (means no UI preview update, and skips saving)
            return {}
        
        # If switch is ON, delegate to standard ComfyUI SaveImage logic
        return super().save_images(
            images=images, 
            filename_prefix=filename_prefix, 
            prompt=prompt, 
            extra_pnginfo=extra_pnginfo
        )