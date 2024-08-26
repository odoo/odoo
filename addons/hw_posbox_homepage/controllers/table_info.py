from typing import NamedTuple


class TableInfo(NamedTuple):
    """A named tuple to represent a table row in an IoT pages"""
    name: str
    """The name of the row. Will correspond to the first column"""
    value: str = None
    """The value of the row. Will correspond to the second column. Can be raw HTML"""
    action_url: str = None
    """If filled, a button will automatically be created next to the value."""
    action_name: str = 'configure'
    """text shown on the button"""
    action_target: str = None
    """target of the action <a> tag. Generally '_blank' for opening a new tab"""
    name_icon: str = None
    """font awesome icon class to show before the name"""
    action_iot_documentation_url: str = None
    """URL to the IoT documentation for the action.
    Will be used instead of `action_url` if provided."""
    iot_documentation_url: str = None
    """URL to the IoT documentation for the row. Will be displayed next to the name"""
    is_warning: bool = False
    """If True, the row will be highlighted as a warning"""
