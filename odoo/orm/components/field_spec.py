"""Immutable field metadata — testable without ORM runtime.

This module provides :class:`FieldSpec`, a frozen dataclass that captures
a field's *definition* (type, constraints, dependencies) without any
runtime behavior (no cache access, no DB queries, no recomputation).

FieldSpec enables:

* **Validation** — check field definitions for inconsistencies without
  loading modules.
* **Dependency analysis** — build compute graphs from frozen metadata.
* **Serialization** — field definitions as plain data, suitable for
  export, comparison, or migration tooling.

Usage::

    spec = FieldSpec(
        name="total",
        type="float",
        model_name="sale.order",
        store=True,
        compute="_compute_total",
        depends=("line_ids.price",),
    )
    errors = spec.validate()
    assert not errors
    assert spec.is_stored_computed
"""

import dataclasses


@dataclasses.dataclass(frozen=True, slots=True)
class FieldSpec:
    """Immutable snapshot of field metadata.

    All attributes mirror the corresponding :class:`Field` attributes
    at the time the spec is created.  The dataclass is frozen (immutable)
    and uses slots for memory efficiency.
    """

    name: str
    type: str
    model_name: str

    # Storage
    store: bool = True
    column_type: tuple[str, str] | None = None
    index: str | bool | None = None
    company_dependent: bool = False
    translate: bool = False

    # Compute
    compute: str | None = None
    depends: tuple[str, ...] = ()
    depends_context: tuple[str, ...] = ()
    inverse: str | None = None
    precompute: bool = False
    compute_sudo: bool | None = None
    recursive: bool = False

    # Related
    related: str | None = None

    # Constraints
    required: bool = False
    readonly: bool = False
    copy: bool = True

    # Access
    groups: str | None = None

    # Display
    string: str = ""
    help: str = ""

    # Aggregation
    aggregator: str | None = None

    # Relational (populated for relational fields)
    comodel_name: str | None = None
    relation: str | None = None  # Many2many relation table
    ondelete: str | None = None

    # Default
    has_default: bool = False

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def is_stored_computed(self) -> bool:
        """Whether the field is computed and stored in the database."""
        return bool(self.compute and self.store)

    @property
    def is_column(self) -> bool:
        """Whether the field is stored as a database column."""
        return bool(self.store and self.column_type)

    @property
    def is_relational(self) -> bool:
        """Whether the field is a relational type."""
        return self.type in (
            "many2one",
            "one2many",
            "many2many",
            "many2one_reference",
        )

    @property
    def is_computed(self) -> bool:
        """Whether the field has a compute method (stored or not)."""
        return bool(self.compute)

    @property
    def is_related(self) -> bool:
        """Whether the field is a related field."""
        return bool(self.related)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> list[str]:
        """Return a list of validation errors (empty means valid).

        Checks for common definition inconsistencies that would cause
        runtime errors or silent bugs.
        """
        errors: list[str] = []
        prefix = f"{self.model_name}.{self.name}"

        if self.recursive and not self.compute:
            errors.append(f"{prefix}: recursive=True requires compute")

        if self.precompute and not self.compute:
            errors.append(f"{prefix}: precompute=True requires compute")

        if self.inverse and not self.compute:
            errors.append(f"{prefix}: inverse requires compute")

        if self.compute_sudo is not None and not self.compute:
            errors.append(f"{prefix}: compute_sudo requires compute")

        if self.depends and not self.compute and not self.related:
            errors.append(f"{prefix}: depends requires compute or related")

        if self.related and self.compute:
            errors.append(f"{prefix}: cannot have both related and compute")

        if self.comodel_name and not self.is_relational:
            errors.append(f"{prefix}: comodel_name only for relational fields")

        return errors

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        parts = [f"{self.model_name}.{self.name}", f"type={self.type!r}"]
        if self.compute:
            parts.append(f"compute={self.compute!r}")
        if not self.store:
            parts.append("store=False")
        if self.required:
            parts.append("required=True")
        if self.related:
            parts.append(f"related={self.related!r}")
        return f"FieldSpec({', '.join(parts)})"
