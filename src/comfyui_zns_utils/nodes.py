from .basic_image_config import BasicImageConfig
from .switch_any import SwitchAny
from .switch_save_image import SwitchSaveImage
from .clip_text_encode_combined import CLIPTextEncodeCombined
from .dan_tag_gen import DanTagGen

# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "BasicImageConfig": BasicImageConfig,
    "SwitchAny": SwitchAny,
    "SwitchSaveImage": SwitchSaveImage,
    "CLIPTextEncodeCombined": CLIPTextEncodeCombined,
    "DanTagGen": DanTagGen,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "BasicImageConfig": "Basic Image Config",
    "SwitchAny": "Switch Any",
    "SwitchSaveImage": "Switch Save Image",
    "CLIPTextEncodeCombined": "CLIP Text Encode Combined",
    "DanTagGen": "Danbooru Tag Generator",
}

WEB_DIRECTORY = "./src/web"
