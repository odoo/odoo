# Part of Odoo. See LICENSE file for full copyright and licensing details.

from __future__ import annotations

from datetime import UTC
from typing import Any

from odoo import fields
from odoo.tools.json import scriptsafe


class JsonLd:
    """
    Fluent builder for creating Schema.org JSON-LD structured data.

    Example:
        >>> product = JsonLd("Product", {
        ...     "name": "Laptop",
        ...     "sku": "LAP-001",
        ...     "price": 999.99,
        ... })
        >>> offer = JsonLd("Offer", {
        ...     "price": 999.99,
        ...     "priceCurrency": "USD",
        ...     "availability": "https://schema.org/InStock"
        ... })
        >>> product.add_nested({"offers": offer})

        >>> JsonLd.render_structured_data([product])
    """
    __slots__ = ("schema_type", "values")

    def __init__(self, schema_type: str, /, values: dict[str, Any] | None = None):
        self.schema_type = schema_type
        self.values = {}
        if values:
            self.set(values)

    @staticmethod
    def _has_invalid_types(values, expected_type: type) -> list[str]:
        """Return class names of items that are not instances of *expected_type*,
        in the order they first appear."""
        return list(dict.fromkeys(
            v.__class__.__name__
            for v in values
            if v is not None and not isinstance(v, expected_type)
        ))

    @staticmethod
    def render_structured_data(builders: list[JsonLd]) -> str | bool:
        """Render a list of JsonLd builders into a JSON-LD string.
        Falsy values (e.g., None) are ignored. If no valid builders remain,
        returns False.
        Args:
            builders: A list of JsonLd instances.
        Returns:
            A JSON string containing the rendered JSON-LD data, or False if
            the list is empty or contains no valid builders.
        Raises:
            TypeError: If any item in *builders* is not a JsonLd instance.
        Example:
            >>> org = JsonLd('Organization', {'name': 'Example Corp'})
            >>> website = JsonLd('WebSite', {'name': 'Example Site', 'url': 'https://example.com'})
            >>> JsonLd.render_structured_data([org, website])
            >>> Output: [
                {
                    '@type': 'Organization',
                    '@context': 'https://schema.org',
                    'name': 'Example Corp'
                },
                {
                    '@type': 'WebSite',
                    '@context': 'https://schema.org',
                    'name': 'Example Site',
                    'url': 'https://example.com'
                }
            ]
        """
        if not builders:
            return False
        invalid = JsonLd._has_invalid_types(builders, JsonLd)
        if invalid:
            raise TypeError(
                f"render_structured_data() expects JsonLd instances, "
                f"got: {', '.join(invalid)}",
            )
        rendered = [b._to_jsonld_dict() for b in builders if b]
        if not rendered:
            return False
        return scriptsafe.dumps(rendered, ensure_ascii=False)

    @staticmethod
    def to_iso_datetime(dt) -> str | None:
        """Convert datetime to ISO-8601 string with timezone information.
        As per https://schema.org/DateTime, the value must be in ISO-8601 format
        and include timezone information.
        Args:
            dt: Datetime object or compatible value
        Returns:
            ISO-8601 formatted string with timezone, or None if dt is falsy
            or cannot be converted.
        Example:
            >>> from datetime import datetime
            >>> dt = datetime(2025, 1, 15, 10, 30)
            >>> JsonLd.to_iso_datetime(dt)
            '2025-01-15T10:30:00+00:00'
        """
        as_datetime = fields.Datetime.to_datetime(dt)
        if not as_datetime:
            return None
        if not as_datetime.tzinfo:
            as_datetime = as_datetime.replace(tzinfo=UTC)
        return as_datetime.isoformat()

    def get(self, key: str, default=None):
        """Retrieve a stored value by key.
        Args:
            key: Property name
            default: Value returned when the key is absent.
        Returns:
            The stored value, or *default*.
        """
        return self.values.get(key, default)

    def set(self, values: dict[str, Any]) -> JsonLd:
        """Set properties on the schema (overwrites existing keys).
        Properties are automatically converted from snake_case to camelCase.
        Args:
            values: Property name-value pairs
        Returns:
            Self for method chaining
        Example:
            >>> product = JsonLd('Product')
            >>> product.set({'name': 'Widget', 'price': 29.99, 'brand': 'BrandName'})
        """
        for key, value in values.items():
            if value is None:
                continue
            items = value if isinstance(value, list) else [value]
            if any(isinstance(v, JsonLd) for v in items):
                raise TypeError(f"Key '{key}' contains JsonLd value(s). Use add_nested() instead.")
            self.values[key] = value
        return self

    def add_nested(self, values: dict[str, JsonLd | list[JsonLd] | None]) -> JsonLd:
        """Add nested schema builder(s).
        A single nested value is stored as-is; values are converted to a list
        only when multiple nested values exist for the same key. None values
        are ignored.
        Args:
            values: Property name to JsonLd (or list of them) mapping
        Returns:
            Self for method chaining
        Example:
            >>> product = JsonLd('Product', {'name': 'Widget'})
            >>> offer = JsonLd('Offer', {'price': 99.99, 'priceCurrency': 'USD'})
            >>> product.add_nested({'offers': offer})
            >>> isinstance(product.get('offers'), JsonLd)
            True
            >>>
            >>> # Adding another nested item appends to the existing value
            >>> offer2 = JsonLd('Offer', {'price': 79.99, 'priceCurrency': 'EUR'})
            >>> product.add_nested({'offers': offer2})  # offers is now [offer, offer2]
            >>>
            >>> # Multiple nested items at once
            >>> product.add_nested({'offers': [offer1, offer2, offer3]})
        """
        for key, builder in values.items():
            if builder is None:
                continue
            items = builder if isinstance(builder, list) else [builder]
            if not items:
                continue
            invalid = self._has_invalid_types(items, JsonLd)
            if invalid:
                raise TypeError(
                    f"add_nested() expects JsonLd instances for key '{key}', "
                    f"got: {', '.join(invalid)}")
            existing = self.values.get(key)
            if existing is None:
                self.values[key] = items[0] if len(items) == 1 else items
            elif isinstance(existing, JsonLd):
                self.values[key] = [existing, *items]
            elif isinstance(existing, list):
                is_jsonld_list = isinstance(existing[0], JsonLd)
                if not is_jsonld_list:
                    raise TypeError(f"Cannot append to '{key}', existing value is not a list of JsonLd")
                existing.extend(items)
            else:
                raise TypeError(f"Cannot append to '{key}', existing type: {existing.__class__.__name__}")
        return self

    def _to_jsonld_dict(self, include_context: bool = True) -> dict[str, Any]:
        """Convert this builder to a JSON-LD dictionary.
        Args:
            include_context: Whether to include @context
        Returns:
            JSON-LD dictionary
        """
        normalized_values = {}
        for key, value in self.values.items():
            v = self._normalize_value(value)
            if v is not None:
                normalized_values[key] = v
        # Only @id -> reference object
        if len(normalized_values) == 1 and '@id' in normalized_values:
            return normalized_values
        data: dict[str, Any] = {}
        if include_context:
            data['@context'] = 'https://schema.org'
        data['@type'] = self.schema_type
        data.update(normalized_values)
        return data

    def _normalize_value(self, value):
        """Normalize a value for JSON-LD rendering."""
        # False is also treated as value. None and empty lists are ignored.
        if value is None:
            return None
        if isinstance(value, JsonLd):
            return value._to_jsonld_dict(include_context=False)
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
