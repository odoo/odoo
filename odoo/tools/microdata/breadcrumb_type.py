from __future__ import annotations
from .core.object_type import ListItem, Thing, ItemList


class BreadcrumbList(ItemList):
    __definition__ = """
        A BreadcrumbList is an ItemList consisting of a chain of linked Web
        pages, typically described using at least their URL and their name,
        and typically ending with the current page.
    """
    __gsc_required_properties__ = [
        "itemListElement",
        ("itemListElement.item", "unless_last_element"),
        "itemListElement.position",
        "itemListElement.name"
    ]

    def __init__(self,
                 item_list_element: list[ListItem | Thing],
                 item_list_order: str | None = None,
                 number_of_items: int | None = None,
                 **kwargs) -> None:
        super().__init__(
            item_list_element=item_list_element,
            item_list_order=item_list_order,
            number_of_items=number_of_items,
            **kwargs)
