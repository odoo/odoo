# Part of Odoo. See LICENSE file for full copyright and licensing details.

# TODO: This module should be moved to 'tools/structure_data'?

"""
Schema.org JSON-LD Builder for Website module(s).

Simple builder for creating Schema.org structured data with automatic
snake_case to camelCase conversion.

Usage:
    >>> product = SchemaBuilder("Product", name="Widget", brand="BrandCo")
    >>>
    >>> offer = SchemaBuilder("Offer", price=99.99, price_currency="USD")
    >>> product.add_nested(offers=offer)
    >>>
    >>> json_ld = product.render_json()
"""
from __future__ import annotations

from datetime import timezone
from typing import Any

from odoo import fields
from odoo.tools.json import scriptsafe


class SchemaBuilder:
    """
    Fluent builder for creating Schema.org JSON-LD structures.

    Features:
        - Automatic snake_case to camelCase conversion
        - Nested schema support
        - Multiple value support for array properties
        - Method chaining for clean API

    Example:
        >>> product = SchemaBuilder("Product", name="Laptop", sku="LAP-001")
        >>>
        >>> offer = SchemaBuilder("Offer", price=999.99, price_currency="USD")
        >>> product.add_nested(offers=offer)
        >>>
        >>> json_ld = product.render_json()
    """
    __slots__ = ("schema_type", "values")

    def __init__(self, schema_type: str, /, **kwargs):
        self.schema_type = schema_type
        self.values: dict[str, Any] = {}
        if kwargs:
            self.set(**kwargs)

    @staticmethod
    def _normalize_key(key: str) -> str:
        """ Normalize a property key to JSON-LD format.
        Converts snake_case to camelCase and handles special cases.
        """
        if key == 'id':
            return '@id'
        if "_" not in key:
            return key

        parts = key.split("_")
        # Special handling: *_id becomes *ID (e.g., product_id -> productID)
        if parts[-1] == "id":
            return parts[0] + "".join(p.capitalize() for p in parts[1:-1]) + "ID"
        return parts[0] + "".join(p.capitalize() for p in parts[1:])

    def set(self, **kwargs) -> SchemaBuilder:
        """
        Set properties on the schema.
        Properties are automatically converted from snake_case to camelCase.

        Args:
            **kwargs: Property name-value pairs

        Returns:
            Self for method chaining

        Example:
            >>> product = SchemaBuilder("Product")
            >>> product.set(name="Widget", price=29.99, brand="BrandName")
        """
        for raw_key, value in kwargs.items():
            key = self._normalize_key(raw_key)
            self.values[key] = value
        return self

    def add_nested(self, **kwargs) -> SchemaBuilder:
        """
        Add nested schema builder(s).

        Automatically handles single values vs arrays.

        Args:
            **kwargs: Property name to SchemaBuilder mapping

        Returns:
            Self for method chaining

        Example:
            >>> product = SchemaBuilder("Product", name="Widget")
            >>> offer = SchemaBuilder("Offer", price=99.99, price_currency="USD")
            >>> product.add_nested(offers=offer)
            >>>
            >>> # Multiple nested items
            >>> product.add_nested(offers=[offer1, offer2, offer3])
        """
        for raw_key, builder in kwargs.items():
            if not builder:
                continue

            key = self._normalize_key(raw_key)
            if isinstance(builder, (list, tuple)):
                # Multiple nested items
                self.values.setdefault(key, []).extend(builder)
            else:
                # Single nested item - check if we should append or replace
                if key in self.values and isinstance(self.values[key], list):
                    self.values[key].append(builder)
                else:
                    # Not an array yet, just set
                    self.values[key] = builder

        return self

    @staticmethod
    def datetime(dt):
        """
        Convert datetime to ISO-8601 string with timezone information.

        Args:
            dt: Datetime object or compatible value

        Returns:
            ISO-8601 formatted string with timezone, or False if dt is falsy

        Example:
            >>> from datetime import datetime
            >>> dt = datetime(2025, 1, 15, 10, 30)
            >>> SchemaBuilder.datetime(dt)
            '2025-01-15T10:30:00+00:00'
        """
        if not dt:
            return False
        as_datetime = fields.Datetime.to_datetime(dt)
        if as_datetime and not as_datetime.tzinfo:
            as_datetime = as_datetime.replace(tzinfo=timezone.utc)
        return as_datetime.isoformat() if as_datetime else None

    def render_json(self, *, indent: int = 2) -> str:
        """
        Render the schema as JSON-LD string.

        Args:
            indent: JSON indentation level (default: 2)

        Returns:
            JSON-LD string ready for use in HTML

        Example:
            >>> product = SchemaBuilder("Product", name="Widget")
            >>> json_ld = product.render_json()
        """
        return scriptsafe.dumps(self._render(), indent=indent)

    def _render(self, include_context: bool = True) -> dict[str, Any]:
        """
        Render to dictionary.

        Args:
            include_context: Whether to include @context

        Returns:
            JSON-LD dictionary
        """
        data = {"@type": self.schema_type}

        if include_context:
            data["@context"] = "https://schema.org"

        for key, value in self.values.items():
            normalized = self._normalize_value(value)
            if normalized is not None and normalized != []:
                data[key] = normalized

        return data

    def _normalize_value(self, value):
        """Normalize a value for JSON-LD rendering."""
        if value is None or value is False:
            return None

        if isinstance(value, SchemaBuilder):
            return value._render(include_context=False)

        if isinstance(value, (list, tuple)):
            normalized = [
                self._normalize_value(v)
                for v in value
                if v is not None and v is not False
            ]
            if not normalized:
                return None
            # Single item arrays can be unwrapped
            return normalized if len(normalized) > 1 else normalized[0]

        return value

    @staticmethod
    def render_structured_data_list(builders, *, indent=2):
        """
        Render multiple schemas as JSON-LD array.

        Args:
            builders: List of SchemaBuilder instances
            indent: JSON indentation level (default: 2)

        Returns:
            JSON-LD array string, or False if builders is empty

        Example:
            >>> org = SchemaBuilder("Organization", name="Example Corp")
            >>> website = SchemaBuilder("WebSite", name="Example Site", url="https://example.com")
            >>> json_ld = SchemaBuilder.render_structured_data_list([org, website])
        """
        if not builders:
            return False
        return scriptsafe.dumps([b._render() for b in builders], indent=indent)

    @staticmethod
    def create_id_reference(schema_type: str, id_value: str):
        """
        Create a schema reference by @id (for avoiding duplication).

        Useful when referencing an entity defined elsewhere on the page.

        Args:
            schema_type: The schema type
            id_value: The @id value (URL)

        Returns:
            SchemaBuilder with only @type and @id set

        Example:
            >>> # Define organization once
            >>> org = SchemaBuilder("Organization",
            ...                     id="https://example.com/#org",
            ...                     name="Example Corp")
            >>>
            >>> # Reference it elsewhere
            >>> person = SchemaBuilder("Person", name="John Doe")
            >>> org_ref = SchemaBuilder.create_id_reference(
            ...     "Organization",
            ...     "https://example.com/#org"
            ... )
            >>> person.add_nested(works_for=org_ref)
        """
        # TODO: Maybe just lower the schema_type and add it to the id_value(URL)?
        ref = SchemaBuilder(schema_type)
        ref.values['@id'] = id_value
        return ref


def create_breadcrumbs(items: list[tuple[str, str] | None]) -> SchemaBuilder:
    """
    Helper to create a BreadcrumbList.

    Args:
        items: List of (name, url) tuples (None items are automatically filtered)

    Returns:
        SchemaBuilder for BreadcrumbList

    Example:
        >>> breadcrumbs = create_breadcrumbs([
        ...     ("Home", "https://example.com/"),
        ...     ("Products", "https://example.com/products") if show_products else None,
        ...     ("Widget", "https://example.com/products/widget")
        ... ])
        >>> json_ld = breadcrumbs.render_json()
    """
    # Filter out None items
    valid_items = [item for item in items if item is not None]

    # TODO: Is there any limitation?
    # if len(valid_items) == 0:
    #     return None
    # elif len(valid_items) > 3:
    #     raise ValueError("BreadcrumbList should have between 1 and 3 items")
    # Do we even have limitations? Let's decide in 2nd round cleanup

    list_items = []
    for position, (name, url) in enumerate(valid_items, start=1):
        item = SchemaBuilder("ListItem", position=position, name=name, item=url)
        list_items.append(item)

    breadcrumbs = SchemaBuilder("BreadcrumbList")
    breadcrumbs.add_nested(item_list_element=list_items)

    return breadcrumbs
