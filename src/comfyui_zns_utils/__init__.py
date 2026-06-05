"""
ZNS ComfyUI Utils - Utility nodes and extensions for ComfyUI.

This module exports all available nodes and installs the SwitchAny validation hook
that intercepts prompt validation to enable flow control.
"""

from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from .switch_any import find_switch_any, resolve_switch_boolean, block_switch

# Import execution module from ComfyUI to hijack validation
try:
    import execution
    COMFY_EXECUTION_AVAILABLE = True
except ImportError:
    COMFY_EXECUTION_AVAILABLE = False

# Store the original validation function
original_validate = None


async def hijack_validate_with_switch(*args, **kwargs):
    """
    Hijack ComfyUI's prompt validation to enable SwitchAny flow control.
    
    This function intercepts the validation process before execution to:
    1. Find all SwitchAny nodes in the prompt
    2. Resolve their switch boolean values
    3. Remove downstream nodes when switch is OFF
    4. Call the original validation on the modified prompt
    """
    # Extract the prompt dict from args
    prompt = None
    for arg in args:
        if isinstance(arg, dict) and any(
            isinstance(v, dict) and "class_type" in v for v in arg.values()
        ):
            prompt = arg
            break

    if prompt is None:
        # No valid prompt found, call original validation
        return await original_validate(*args, **kwargs)

    # Find all SwitchAny nodes
    switch_ids = find_switch_any(prompt)

    if not switch_ids:
        # No SwitchAny nodes found, proceed normally
        return await original_validate(*args, **kwargs)

    # Process each SwitchAny node
    for switch_id in switch_ids:
        if switch_id not in prompt:
            continue

        try:
            # Extract the switch value
            switch_value = prompt[switch_id]["inputs"].get("switch", False)

            # Resolve the boolean (handle direct values and connected nodes)
            switch_enabled = resolve_switch_boolean(prompt, switch_value)

            # Block downstream nodes if switch is OFF
            if not switch_enabled:
                prompt = block_switch(prompt, switch_id, switch_enabled)

        except ValueError as e:
            # Error resolving the boolean - return validation error
            return (
                False,
                {
                    "type": "switch_any_invalid_boolean",
                    "message": "Switch Any: Unable to Determine Boolean",
                    "details": str(e),
                    "extra_info": {},
                },
                [],
                [],
            )
        except Exception as e:
            # Unexpected error - return validation error
            return (
                False,
                {
                    "type": "switch_any_error",
                    "message": "Switch Any: Unexpected Error",
                    "details": str(e),
                    "extra_info": {},
                },
                [],
                [],
            )

    # Call original validation with modified prompt
    return await original_validate(*args, **kwargs)


# Install the validation hook if ComfyUI execution module is available
if COMFY_EXECUTION_AVAILABLE:
    original_validate = execution.validate_prompt
    execution.validate_prompt = hijack_validate_with_switch


__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
]
