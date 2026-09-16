from odoo import api, fields, models
from odoo.tools import SQL

ENTITY_ID_BITS = 28
ENTITY_TABLES = {
    "res.partner": "res_partner",
}


class DocumentComplianceReport(models.Model):
    _name = "document.compliance.report"
    _description = "Document Compliance Report"
    _inherit = ["mixin.sql.report", "mixin.materialized.view"]
    _auto = False
    # The row id is entity_id::bigint * 1000 + <model ordinal>, unique per
    # entity, which is what REFRESH ... CONCURRENTLY needs.
    _relation_index_field = "id"
    _rec_name = "entity_name"
    _order = "compliance_percentage desc"

    entity_name = fields.Char(
        readonly=True,
        help="Name of the entity (partner name, employee name, vehicle plate, etc.)",
    )
    entity_type = fields.Char(
        readonly=True,
        help="Model name of the entity (res.partner, hr.employee, etc.)",
    )
    entity_id = fields.Integer(
        string="Entity ID",
        readonly=True,
        help="Database ID of the entity record",
    )

    total_required = fields.Integer(
        string="Required Document Types",
        readonly=True,
        help="Total number of mandatory document types for this entity",
    )
    total_present = fields.Integer(
        string="Document Types Covered",
        readonly=True,
        help="Number of mandatory document types this entity has at least one document for (including expired)",
    )
    total_valid = fields.Integer(
        string="Valid Document Types",
        readonly=True,
        help="Number of mandatory document types this entity satisfies: it holds at least one document that is valid, or one whose type does not expire",
    )
    total_expiring = fields.Integer(
        string="Expiring Soon Types",
        readonly=True,
        help="Number of mandatory document types whose best document expires within 30 days",
    )
    total_expired = fields.Integer(
        string="Expired Document Types",
        readonly=True,
        help="Number of mandatory document types whose documents are all expired",
    )
    total_missing = fields.Integer(
        string="Missing Document Types",
        readonly=True,
        help="Number of mandatory document types this entity has no assessable document for -- either no document at all, or none carrying an expiration date its type requires",
    )

    compliance_percentage = fields.Float(
        string="Compliance %",
        readonly=True,
        aggregator="avg",
        help="Percentage of mandatory document types with valid documents (total_valid / total_required * 100)",
    )
    is_compliant = fields.Boolean(
        string="Is Fully Compliant",
        readonly=True,
        help="True if entity has valid documents for ALL mandatory document types",
    )
    compliance_state = fields.Selection(
        selection=[
            ("compliant", "Compliant"),
            ("partial", "Partial Compliance"),
            ("non_compliant", "Non-Compliant"),
        ],
        string="Compliance Status",
        readonly=True,
        help="Compliant (has all mandatory types with valid docs), Partial (has some), Non-Compliant (missing required types or all expired)",
    )

    earliest_expiry = fields.Date(
        string="Next Expiry Date",
        readonly=True,
        help="The earliest expiration date across this entity's documents for "
        "the mandatory types it is held to, whether or not they are still valid",
    )
    last_verification = fields.Date(
        string="Last Verification Date",
        readonly=True,
        help="The most recent verification date across this entity's documents "
        "for the mandatory types it is held to",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
        help="Company this report entry belongs to",
    )

    @api.model
    def _get_entity_model_map(self) -> dict[str, str]:
        return {
            model: table for model, table in ENTITY_TABLES.items() if model in self.env
        }

    def _get_entities_union(self) -> str:
        parts = [
            f"SELECT '{model}' AS entity_type, t.id AS entity_id, "
            f"t.company_id FROM {table} t WHERE t.active = true"
            for model, table in self._get_entity_model_map().items()
        ]
        return "\n                UNION ALL\n                ".join(parts)

    def _get_type_scope_conditions(self) -> list[str]:
        """What makes a document type required *of this entity*.

        Joined with AND, so an extension narrows rather than widens: a bridge
        that knows a sub-kind of its entity adds its own clause here.
        """
        return ["dt.applies_to = 'all' OR dt.applies_to = e.entity_type"]

    def _with_cte(self) -> SQL:
        type_scope = " AND ".join(
            f"({condition})" for condition in self._get_type_scope_conditions()
        )
        return SQL(f"""
            entities AS (
                {self._get_entities_union()}
            ),
            entity_doc_types AS (
                SELECT
                    e.entity_type,
                    e.entity_id,
                    e.company_id,
                    dt.id as document_type_id,
                    dt.is_mandatory,
                    COUNT(dd.id) as document_count,
                    -- The four buckets below are a strict ladder, so exactly one
                    -- of them fires per required type and they always sum to
                    -- total_required.
                    --
                    -- They read expiration_state, whose vocabulary this is:
                    -- valid / expiring_soon / expired / missing, and NULL when
                    -- the TYPE does not expire. compliance_state is the other
                    -- field and says compliant / non_compliant / na, so testing
                    -- it for 'valid' matched nothing and every present document
                    -- fell through to is_missing.
                    --
                    -- A NULL expiration_state counts as satisfied -- the type
                    -- does not expire, so there is nothing to be late for -- but
                    -- only for a row that HAS a document. Without the dd.id
                    -- guard the LEFT JOIN's empty row, where every dd column is
                    -- NULL, would read as satisfied and invert the whole report.
                    CASE
                        WHEN MAX(CASE WHEN dd.id IS NOT NULL AND (dd.expiration_state = 'valid' OR dd.expiration_state IS NULL) THEN 1 ELSE 0 END) = 1 THEN 1
                        ELSE 0
                    END as is_valid,
                    -- 'missing' is a document whose type expires and that
                    -- carries no date; it is present but does not satisfy, which
                    -- is how compliance_state grades it too.
                    CASE
                        WHEN MAX(CASE WHEN dd.id IS NOT NULL AND (dd.expiration_state = 'valid' OR dd.expiration_state IS NULL) THEN 1 ELSE 0 END) = 1 THEN 0
                        WHEN MAX(CASE WHEN dd.expiration_state = 'expiring_soon' THEN 1 ELSE 0 END) = 1 THEN 0
                        WHEN MAX(CASE WHEN dd.expiration_state IN ('expired', 'missing') THEN 1 ELSE 0 END) = 1 THEN 1
                        ELSE 0
                    END as is_expired,
                    CASE
                        WHEN MAX(CASE WHEN dd.id IS NOT NULL AND (dd.expiration_state = 'valid' OR dd.expiration_state IS NULL) THEN 1 ELSE 0 END) = 1 THEN 0
                        WHEN MAX(CASE WHEN dd.expiration_state = 'expiring_soon' THEN 1 ELSE 0 END) = 1 THEN 1
                        ELSE 0
                    END as is_expiring,
                    -- No document at all: MAX over zero rows is NULL, which is
                    -- not 1, so every branch above falls through to here.
                    CASE
                        WHEN MAX(CASE WHEN dd.id IS NOT NULL THEN 1 ELSE 0 END) = 1 THEN 0
                        ELSE 1
                    END as is_missing,
                    MIN(dd.date_expiration) FILTER (WHERE dd.date_expiration IS NOT NULL) as earliest_expiry,
                    MAX(dd.date_verification) as last_verification
                FROM entities e
                JOIN document_type dt
                    ON {type_scope}
                LEFT JOIN document_document dd
                    ON dd.res_model = e.entity_type
                    AND dd.res_id = e.entity_id
                    AND dd.document_type_id = dt.id
                    AND dd.active = true
                    AND (dd.company_id IS NULL OR e.company_id IS NULL
                         OR dd.company_id = e.company_id)
                WHERE dt.active = true
                    AND dt.is_mandatory = true
                    AND (dt.company_id = e.company_id
                         OR dt.company_id IS NULL
                         OR e.company_id IS NULL)
                GROUP BY e.entity_type, e.entity_id, e.company_id, dt.id
            )
            """)

    def _get_row_id_expression(self) -> str:
        ordinals = " ".join(
            f"WHEN '{model}' THEN {ordinal}"
            for ordinal, model in enumerate(self._get_entity_model_map())
        )
        # entity_id is int4 on all three entity tables, so the multiplication
        # must be widened: int4 * 1000 raises "integer out of range" from
        # id 2 147 484 on, and it raises for the whole query, not just the row.
        return (
            f"edt.entity_id::bigint * 1000 + "
            f"(CASE edt.entity_type {ordinals} ELSE 999 END)"
        )

    def _get_fields_select(self) -> dict:
        return {
            "id": self._get_row_id_expression(),
            "entity_name": self._get_entity_name_expression(),
            "entity_type": "edt.entity_type",
            "entity_id": "edt.entity_id",
            "total_required": "COUNT(edt.document_type_id)",
            "total_present": "COUNT(edt.document_type_id) FILTER (WHERE edt.document_count > 0)",
            # The CTE's four buckets are a strict ladder emitting 1/0, so each
            # total reads its own bucket: no bucket has to subtract another,
            # and the four sum to total_required.
            "total_valid": "COUNT(edt.document_type_id) FILTER (WHERE edt.is_valid = 1)",
            "total_expiring": "COUNT(edt.document_type_id) FILTER (WHERE edt.is_expiring = 1)",
            "total_expired": "COUNT(edt.document_type_id) FILTER (WHERE edt.is_expired = 1)",
            "total_missing": "COUNT(edt.document_type_id) FILTER (WHERE edt.is_missing = 1)",
            "compliance_percentage": """CASE
                    WHEN COUNT(edt.document_type_id) = 0 THEN 0.0
                    ELSE COUNT(edt.document_type_id) FILTER (WHERE edt.is_valid = 1)::float
                         / COUNT(edt.document_type_id)::float * 100
                END""",
            "is_compliant": "COUNT(edt.document_type_id) FILTER (WHERE edt.is_valid = 1) = COUNT(edt.document_type_id)",
            "compliance_state": """CASE
                    WHEN COUNT(edt.document_type_id) FILTER (WHERE edt.is_valid = 1) = COUNT(edt.document_type_id) THEN 'compliant'
                    WHEN COUNT(edt.document_type_id) FILTER (WHERE edt.is_valid = 1) > 0 THEN 'partial'
                    ELSE 'non_compliant'
                END""",
            "earliest_expiry": "MIN(edt.earliest_expiry)",
            "last_verification": "MAX(edt.last_verification)",
            "company_id": "edt.company_id",
        }

    def _get_from_tables(self) -> list:
        return [("entity_doc_types", "edt", None, None)]

    def _get_fields_group_by(self) -> list:
        return ["edt.entity_type", "edt.entity_id", "edt.company_id"]

    def _get_entity_name_expression(self) -> str:
        model_map = self._get_entity_model_map()

        fallback = "CONCAT(edt.entity_type, ' #', edt.entity_id::text)"

        case_parts = []
        for model, table in model_map.items():
            if model in self.env:
                # COALESCE, not a bare subquery: the ELSE only covers an unknown
                # model, so a known model whose row has a NULL name rendered an
                # empty Entity cell with no id to identify the row by. A stock
                # install already has one -- the private address auto-created
                # under a user's partner.
                case_parts.append(
                    f"WHEN edt.entity_type = '{model}' THEN COALESCE("
                    f"(SELECT name FROM {table} WHERE id = edt.entity_id LIMIT 1), "
                    f"{fallback})"
                )

        case_parts.append(f"ELSE {fallback}")
        return f"CASE {' '.join(case_parts)} END"

    @api.readonly
    def action_view_documents(self):
        self.check_singleton()

        return {
            "name": f"Documents: {self.entity_name}",
            "type": "ir.actions.act_window",
            "res_model": "document.document",
            "view_mode": "kanban,list",
            "domain": [
                ("res_model", "=", self.entity_type),
                ("res_id", "=", self.entity_id),
            ],
            "context": {
                "default_res_model": self.entity_type,
                "default_res_id": self.entity_id,
            },
        }

    @api.readonly
    def action_view_entity(self):
        self.check_singleton()

        if not self.entity_type or not self.entity_id:
            return {"type": "ir.actions.act_window_close"}

        return {
            "name": self.entity_name,
            "type": "ir.actions.act_window",
            "res_model": self.entity_type,
            "res_id": self.entity_id,
            "view_mode": "form",
            "target": "current",
        }
