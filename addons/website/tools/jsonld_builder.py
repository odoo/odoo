# Part of Odoo. See LICENSE file for full copyright and licensing details.

from __future__ import annotations

from datetime import UTC
from typing import Any

from odoo import fields
from odoo.tools.json import scriptsafe


class JsonLd:
    """
    Fluent builder for creating Schema.org JSON-LD structures.
        - Automatic snake_case to camelCase conversion
        - Nested schema support
        - Multiple value support for array properties
        - Method chaining for clean API
    Example:
        >>> product = JsonLd("Product", name="Laptop", sku="LAP-001")
        >>>
        >>> offer = JsonLd("Offer", price=999.99, price_currency="USD")
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
    def _find_invalid_types(values, expected_type: type) -> list[str]:
        """Return class names of items that are not instances of *expected_type*,
        in the order they first appear."""
        return list(dict.fromkeys(
            v.__class__.__name__
            for v in values
            if v is not None and not isinstance(v, expected_type)
        ))

    @staticmethod
    def _normalize_key(key: str) -> str:
        """Normalize a property key to JSON-LD format.
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

    def get(self, key: str, default=None):
        """Retrieve a stored value by its snake_case key.
        The key is normalised exactly like :meth:`set` / :meth:`add_nested`
        so callers never have to know the internal camelCase representation.
        Args:
            key: Property name in snake_case (e.g. ``'offers'``,
                 ``'price_currency'``).
            default: Value returned when the key is absent.
        Returns:
            The stored value, or *default*.
        """
        return self.values.get(self._normalize_key(key), default)

    def set(self, **kwargs) -> JsonLd:
        """Set properties on the schema.
        Properties are automatically converted from snake_case to camelCase.
        Args:
            **kwargs: Property name-value pairs
        Returns:
            Self for method chaining
        Example:
            >>> product = JsonLd("Product")
            >>> product.set(name="Widget", price=29.99, brand="BrandName")
        """
        for raw_key, value in kwargs.items():
            if value is None:
                continue
            key = self._normalize_key(raw_key)
            items = value if isinstance(value, list) else [value]
            if any(isinstance(v, JsonLd) for v in items):
                raise TypeError(f"Use add_nested() for JsonLd values, not set(), key='{raw_key}' has JsonLd value(s)")
            self.values[key] = value
        return self

    def add_nested(self, **kwargs) -> JsonLd:
        """Add nested schema builder(s).
        A single nested value is stored as-is; values are converted to a list
        only when multiple nested values exist for the same key. None values
        are ignored.
        Args:
            **kwargs: Property name to JsonLd (or list of them) mapping
        Returns:
            Self for method chaining
        Example:
            >>> product = JsonLd("Product", name="Widget")
            >>> offer = JsonLd("Offer", price=99.99, price_currency="USD")
            >>> product.add_nested(offers=offer)
            >>> isinstance(product.get("offers"), JsonLd)
            True
            >>>
            >>> # Adding another nested item appends to the existing value
            >>> offer2 = JsonLd("Offer", price=79.99, price_currency="EUR")
            >>> product.add_nested(offers=offer2)  # offers is now [offer, offer2]
            >>>
            >>> # Multiple nested items at once
            >>> product.add_nested(offers=[offer1, offer2, offer3])
        """
        for raw_key, builder in kwargs.items():
            if builder is None:
                continue
            key = self._normalize_key(raw_key)
            items = builder if isinstance(builder, list) else [builder]
            if not items:
                continue
            invalid = self._find_invalid_types(items, JsonLd)
            if invalid:
                raise TypeError(
                    f"add_nested() expects JsonLd instances for key '{raw_key}', "
                    f"got: {', '.join(invalid)}")
            existing = self.values.get(key)
            if existing is None:
                self.values[key] = items[0] if len(items) == 1 else items
            elif isinstance(existing, JsonLd):
                self.values[key] = [existing, *items]
            elif isinstance(existing, list):
                invalid_existing = self._find_invalid_types(existing, JsonLd)
                if invalid_existing:
                    raise TypeError(
                        f"add_nested() cannot append to key '{raw_key}': "
                        f"existing list contains {', '.join(invalid_existing)}, not JsonLd")
                existing.extend(items)
            else:
                raise TypeError(
                    f"add_nested() cannot append to key '{raw_key}': "
                    f"it holds a {existing.__class__.__name__}, not a list of JsonLd")
        return self

    @staticmethod
    def datetime(dt) -> str | None:
        """Convert datetime to ISO-8601 string with timezone information.
        Args:
            dt: Datetime object or compatible value
        Returns:
            ISO-8601 formatted string with timezone, or None if dt is falsy
            or cannot be converted.
        Example:
            >>> from datetime import datetime
            >>> dt = datetime(2025, 1, 15, 10, 30)
            >>> JsonLd.datetime(dt)
            '2025-01-15T10:30:00+00:00'
        """
        as_datetime = fields.Datetime.to_datetime(dt)
        if as_datetime and not as_datetime.tzinfo:
            as_datetime = as_datetime.replace(tzinfo=UTC)
        return as_datetime.isoformat() if as_datetime else None

    def render_json(self) -> str:
        """Render the schema as JSON-LD string.
        Returns:
            JSON-LD string ready for use in HTML
        Example:
            >>> product = JsonLd("Product", name="Widget")
            >>> json_ld = product.render_json()
        """
        return scriptsafe.dumps(self._render(), ensure_ascii=False)

    def _render(self, include_context: bool = True) -> dict[str, Any]:
        """Render to dictionary.
        Args:
            include_context: Whether to include @context
        Returns:
            JSON-LD dictionary
        """
        data: dict[str, Any] = {"@type": self.schema_type}
        if include_context:
            data["@context"] = "https://schema.org"
        for key, value in self.values.items():
            normalized = self._normalize_value(value)
            if normalized is not None:
                data[key] = normalized
        return data

    def _normalize_value(self, value):
        """Normalize a value for JSON-LD rendering."""
        # False is also treated as value. None and empty lists are ignored.
        if value is None:
            return None
        if isinstance(value, JsonLd):
            return value._render(include_context=False)
        if isinstance(value, list):
            normalized = [
                self._normalize_value(v)
                for v in value
                if v is not None
            ]
            if not normalized:
                return None
            # Single item arrays can be unwrapped as per Schema.org spec:
            # a property with one value doesn't need to be wrapped in an array.
            return normalized if len(normalized) > 1 else normalized[0]
        return value

    @staticmethod
    def render_structured_data_list(builders) -> str | bool:
        """Render multiple schemas as JSON-LD array.
        None or empty builders are ignored.
        Args:
            builders: List of JsonLd instances
        Returns:
            JSON-LD array string, or False if builders is empty
        Example:
            >>> org = JsonLd("Organization", name="Example Corp")
            >>> website = JsonLd("WebSite", name="Example Site", url="https://example.com")
            >>> json_ld = JsonLd.render_structured_data_list([org, website])
        """
        if not builders:
            return False
        invalid = JsonLd._find_invalid_types(builders, JsonLd)
        if invalid:
            raise TypeError(
                f"render_structured_data_list() expects JsonLd instances, "
                f"got: {', '.join(invalid)}",
            )
        rendered = [b._render() for b in builders if b]
        if not rendered:
            return False
        return scriptsafe.dumps(rendered, ensure_ascii=False)

    @staticmethod
    def create_id_reference(schema_type: str, id_value: str) -> JsonLd:
        """
        Create a schema reference by @id (for avoiding duplication).
        Useful when referencing an entity defined elsewhere on the page.
        Args:
            schema_type: The schema type
            id_value: The @id value (URL)
        Returns:
            JsonLd with only @type and @id set
        Example:
            >>> # Define organization once
            >>> org = JsonLd("Organization",
            ...     id="https://example.com/#org",
            ...     name="Example Corp"
            ... )
            >>> # Reference it elsewhere
            >>> person = JsonLd("Person", name="John Doe")
            >>> org_ref = JsonLd.create_id_reference(
            ...     "Organization",
            ...     "https://example.com/#org"
            ... )
            >>> person.add_nested(works_for=org_ref)
        """
        if not id_value:
            raise ValueError("id_value must be a non-empty string")  # noqa: EM101
        return JsonLd(schema_type, id=id_value)


def create_breadcrumbs(items: list[tuple[str, str] | None]) -> JsonLd | None:
    """
    Helper to create a BreadcrumbList.
    Args:
        items: List of (name, url) tuples (None items are automatically filtered)
    Returns:
        JsonLd for BreadcrumbList, or None if no valid items
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
    if not valid_items:
        return None
    list_items = []
    for position, (name, url) in enumerate(valid_items, start=1):
        item = JsonLd("ListItem", position=position, name=name, item=url)
        list_items.append(item)
    breadcrumbs = JsonLd("BreadcrumbList")
    breadcrumbs.add_nested(item_list_element=list_items)
    return breadcrumbs
