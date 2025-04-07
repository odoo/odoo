from __future__ import annotations
from .object_type import StructuredValue
from .action_type import ConsumeAction, WatchAction


class InteractionCounter(StructuredValue):
    __definition__ = "A summary of how users have interacted with this CreativeWork. In most cases, authors will use a subtype to specify the specific type of interaction."
    __schema_properties__ = StructuredValue.__schema_properties__ | {
        "endTime": ["DateTime", "Time"],
        "interactionService": ["SoftwareApplication", "WebSite"],
        "interactionType": "Action",
        "location": ["Place", "PostalAddress", "Text", "VirtualLocation"],
        "startTime": ["DateTime", "Time"],
        "userInteractionCount": "Integer"
    }

    def __init__(self,
                 user_interaction_count: int,
                 interaction_type: ConsumeAction = WatchAction,
                 **kwargs
                ) -> None:
        if user_interaction_count < 0:
            raise ValueError("user_interaction_count must be a non-negative integer.")
        super().__init__(
            user_interaction_count=user_interaction_count,
            interaction_type=interaction_type,
            **kwargs
        )
