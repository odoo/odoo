from __future__ import annotations
from .core.object_type import ItemList, ListItem
from .core.movie_type import Movie
from .core.how_to_type import Recipe
from .core.local_business_type import Restaurant
from .course_info_type import Course


class Carousel(ItemList):
    __type_name__ = "ItemList"

    def __init__(self,
                 items=list[Course] | list[Movie] | list[Recipe] | list[Restaurant]) -> None:
        item_list_elements = []
        for idx, item in enumerate(items):
            item_list_elements.append(
                ListItem(position=idx + 1, item=item)
            )
        super().__init__(item_list_element=item_list_elements)
