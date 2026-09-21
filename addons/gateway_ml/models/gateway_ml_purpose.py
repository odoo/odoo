from odoo import api, fields, models


class GatewayMlPurpose(models.Model):
    _name = "gateway.ml.purpose"
    _description = "Machine-Learning Purpose"
    _rec_name = "key"
    _order = "key"

    key = fields.Char(
        index=True,
        required=True,
        help="Dotted name a caller gives its requests, e.g. speech.transcription.call. "
        "A policy on speech.transcription also governs speech.transcription.call.",
    )
    name = fields.Char(translate=True)
    sensitive = fields.Boolean(
        help="Requests for a sensitive purpose reach no vendor until a policy of the "
        "company names one.",
    )
    policy_ids = fields.One2many(
        comodel_name="gateway.ml.policy",
        inverse_name="purpose_id",
    )

    _key_uniq = models.Constraint("unique(key)", "A purpose is declared once.")

    @api.model
    def _get_for(self, key: str) -> GatewayMlPurpose:
        purposes = self.sudo().with_context(active_test=False)
        found = purposes.search([("key", "=", key)], limit=1)
        if found:
            return found
        return purposes.create({"key": key})

    @api.model
    def _lineage(self, key: str) -> list[str]:
        parts = key.split(".")
        return [".".join(parts[:end]) for end in range(len(parts), 0, -1)]

    @api.model
    def _is_sensitive(self, key: str) -> bool:
        return bool(
            self.sudo().search_count(
                [("key", "in", self._lineage(key)), ("sensitive", "=", True)], limit=1
            )
        )
