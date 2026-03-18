from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.qbo_bridge.services.qbo_sync_engine import QBOSyncEngine


class QboStandardAccountSyncWizard(models.TransientModel):
    _name = "qbo.standard.account.sync.wizard"
    _description = "Sync standard chart account"

    standard_account_id = fields.Many2one(
        "qbo.standard.account",
        string="Standard account",
        required=True,
    )
    entry_type = fields.Selection(related="standard_account_id.entry_type", readonly=True)
    odoo_account_type = fields.Selection(
        related="standard_account_id.odoo_account_type",
        readonly=True,
    )
    mapping_ids = fields.Many2many(
        "qbo.company.mapping",
        string="Target mappings",
        required=True,
        domain=[("sync_enabled", "=", True)],
    )
    push_to_qbo = fields.Boolean(
        string="Push to QBO after applying to company account",
        default=True,
    )
    update_existing = fields.Boolean(
        string="Update existing company accounts",
        default=True,
    )
    result_message = fields.Text(readonly=True)
    state = fields.Selection(
        [("ready", "Ready"), ("done", "Done")],
        default="ready",
    )

    def action_sync(self):
        self.ensure_one()
        standard_account = self.standard_account_id
        if standard_account.entry_type != "detail":
            raise UserError(_("Only detail standard accounts can be synced to QBO mappings."))
        if not standard_account.odoo_account_type:
            raise UserError(_("Set an Odoo account type before syncing this standard account."))

        created = updated = pushed = skipped = errors = 0
        lines = []
        for mapping in self.mapping_ids:
            try:
                account_model = self.env["account.account"].with_company(mapping.company_id)
                account = account_model.search(
                    [
                        ("company_ids", "=", mapping.company_id.id),
                        ("qbo_standard_account_id", "=", standard_account.id),
                    ],
                    limit=1,
                )
                if not account:
                    account = account_model.search(
                        [
                            ("company_ids", "=", mapping.company_id.id),
                            ("code", "=", standard_account.code),
                        ],
                        limit=1,
                    )

                vals = standard_account.prepare_company_account_vals(mapping.company_id)
                if account:
                    if not self.update_existing:
                        skipped += 1
                        lines.append(_("%s: skipped existing account %s") % (mapping.display_name, account.code))
                        continue
                    account.write(vals)
                    updated += 1
                else:
                    account = account_model.create(vals)
                    created += 1

                if self.push_to_qbo:
                    engine = QBOSyncEngine(self.env, mapping)
                    engine.push_account_record(account)
                    pushed += 1

                lines.append(
                    _("%s: applied %s %s") % (
                        mapping.display_name,
                        account.code,
                        account.name,
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                errors += 1
                lines.append(_("%s: %s") % (mapping.display_name, exc))

        self.result_message = _(
            "Standard account sync complete.\n"
            "Created: %(created)s\n"
            "Updated: %(updated)s\n"
            "Pushed to QBO: %(pushed)s\n"
            "Skipped: %(skipped)s\n"
            "Errors: %(errors)s\n\n"
            "%(lines)s",
        ) % {
            "created": created,
            "updated": updated,
            "pushed": pushed,
            "skipped": skipped,
            "errors": errors,
            "lines": "\n".join(lines),
        }
        self.state = "done"
        return self._stay_open()

    def _stay_open(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
