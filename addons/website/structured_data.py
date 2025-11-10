"""Structured data helpers for schema.org compliant JSON-LD output."""

from datetime import timezone

from odoo.tools.json import scriptsafe as json_safe
from odoo import fields


class StructuredData:
    """Represent a schema.org node with helpers to build JSON-LD structures."""

    __context_url__ = None

    def __init__(self, schema_type, **properties):
        """Initialize the node, normalizing incoming properties."""
        self.schema_type = schema_type
        self.context_url = self.__context_url__ or "https://schema.org"
        self.properties = {
            self._normalize_key(key): self._normalize_value(value, include_context=False)
            for key, value in properties.items()
        }

    def _normalize_key(self, key):
        """Transform Python-friendly keys into schema.org camelCase.

        Returns:
            str: Normalized key, with ``id`` rewritten to ``@id``.
        """
        if not isinstance(key, str) or "_" not in key:
            if key == 'id':
                return '@id'
            return key
        parts = key.split("_")
        return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])

    def _normalize_value(self, value, *, include_context=False):
        """Convert StructuredData instances and iterables into JSON-serializable structures.

        Returns:
            Any: Normalized value ready for JSON serialization.
        """
        if isinstance(value, StructuredData):
            return value.dump(include_context=include_context)
        if isinstance(value, (list, tuple, set)):
            normalized = [self._normalize_value(item, include_context=False) for item in value]
            normalized = [item for item in normalized if item not in (None, False)]
            return normalized or None
        if isinstance(value, dict):
            return {
                self._normalize_key(key): self._normalize_value(val, include_context=False)
                for key, val in value.items()
            }
        return value

    def add(self, property_name, structured_data):
        """Attach a structured data entry to a property, handling multiple values."""
        if structured_data in (None, False):
            return
        normalized_name = self._normalize_key(property_name)
        value = self._normalize_value(structured_data)
        if value in (None, False):
            return

        if normalized_name not in self.properties:
            self.properties[normalized_name] = value
            return

        existing_value = self.properties[normalized_name]
        if existing_value in (None, False):
            self.properties[normalized_name] = value
            return
        if not isinstance(existing_value, list):
            existing_list = [existing_value]
        else:
            existing_list = existing_value
        if isinstance(value, list):
            existing_list.extend(value)
        else:
            existing_list.append(value)
        self.properties[normalized_name] = existing_list

    def dump(self, *, include_context=True):
        """Serialize the node to a JSON-LD compatible dict.

        Returns:
            dict: JSON-LD representation of the node.
        """
        data = {'@type': self.schema_type}
        if include_context:
            data['@context'] = self.context_url
        for key, value in self.properties.items():
            normalized = self._normalize_value(value, include_context=False)
            if normalized in (None, False):
                continue
            if isinstance(normalized, (list, tuple, set)) and len(normalized) == 0:
                continue
            data[key] = normalized
        return data

    def dumps(self):
        """Serialize the node to a JSON-LD formatted string.

        Returns:
            str: JSON-LD string.
        """
        return json_safe.dumps(self.dump(include_context=True), indent=2)

    @staticmethod
    def list_dump(SD_list):
        """Serialize a list of nodes as plain dictionaries.

        Returns:
            list: JSON-LD compatible dictionaries.
        """
        dumps = []
        for entry in SD_list or []:
            if entry in (None, False):
                continue
            if isinstance(entry, StructuredData):
                dumps.append(entry.dump())
            else:
                dumps.append(entry)
        return dumps

    @staticmethod
    def list_dumps(SD_list):
        """Serialize a list of nodes to JSON-LD formatted string.

        Returns:
            str: JSON string containing the nodes.
        """
        return json_safe.dumps(StructuredData.list_dump(SD_list), indent=2)

    @staticmethod
    def collection_page(*, name, url, has_part=None):
        """Return a CollectionPage node.

        Returns:
            StructuredData: Structured data node describing the collection.
        """
        return StructuredData(
            "CollectionPage",
            name=name,
            url=url,
            has_part=has_part
        )

    @staticmethod
    def list_item(*, position, name, item=None):
        """Return a ListItem node describing a breadcrumb entry.

        Returns:
            StructuredData | bool: Structured data node or ``False`` when name is empty.
        """
        if not name:
            return False
        entry = StructuredData("ListItem", position=position, name=name)
        if item:
            entry.add("item", item)
        return entry

    @staticmethod
    def breadcrumb_list(items):
        """Return a BreadcrumbList built from ``(name, url)`` tuples.

        Returns:
            StructuredData | bool: Structured data node or ``False`` when empty.
        """
        elements = []
        for idx, (name, url) in enumerate(items, start=1):
            list_item = StructuredData.list_item(position=idx, name=name, item=url)
            if list_item:
                elements.append(list_item)
        if not elements:
            return False
        return StructuredData('BreadcrumbList', item_list_element=elements)

    @staticmethod
    def datetime(dt):
        """Return an ISO-8601 string with timezone information.

        Returns:
            str | bool: Formatted timestamp or ``False`` when ``dt`` is falsy.
        """
        if not dt:
            return False
        as_datetime = fields.Datetime.to_datetime(dt)
        if not as_datetime.tzinfo:
            as_datetime = as_datetime.replace(tzinfo=timezone.utc)
        return as_datetime.isoformat()
