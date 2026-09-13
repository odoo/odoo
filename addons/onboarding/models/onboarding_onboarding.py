from odoo import api, fields, models

from odoo.addons.onboarding.models.onboarding_progress import ONBOARDING_PROGRESS_STATES


class OnboardingOnboarding(models.Model):
    _name = "onboarding.onboarding"
    _description = "Onboarding"
    _order = "sequence asc, id desc"

    name = fields.Char(
        string="Name of the onboarding",
        translate=True,
    )
    # One word identifier of the onboarding panel, used as its key by the modules that render it.
    route_name = fields.Char(
        string="One word name",
        required=True,
    )
    step_ids = fields.Many2many(
        comodel_name="onboarding.onboarding.step",
        string="Onboarding steps",
    )

    text_completed = fields.Char(
        string="Message at completion",
        default=lambda s: s.env._("Nice work! Your configuration is done."),
        help="Text shown on onboarding when completed",
    )

    is_per_company = fields.Boolean(
        string="Should be done per company?",
        compute="_compute_is_per_company",
        store=False,
        readonly=True,
    )
    panel_close_action_name = fields.Char(
        string="Closing action",
        help="Name of the onboarding model action to execute when closing the panel.",
    )

    current_progress_id = fields.Many2one(
        comodel_name="onboarding.progress",
        string="Onboarding Progress",
        compute="_compute_current_progress",
        help="Onboarding Progress for the current context (company).",
    )
    current_onboarding_state = fields.Selection(
        selection=ONBOARDING_PROGRESS_STATES,
        string="Completion State",
        compute="_compute_current_progress",
        readonly=True,
    )
    is_onboarding_closed = fields.Boolean(
        string="Was panel closed?",
        compute="_compute_current_progress",
    )

    progress_ids = fields.One2many(
        comodel_name="onboarding.progress",
        inverse_name="onboarding_id",
        string="Onboarding Progress Records",
        readonly=True,
        help="All Onboarding Progress Records (across companies).",
    )

    sequence = fields.Integer(default=10)
    _route_name_uniq = models.Constraint(
        "UNIQUE (route_name)",
        "Onboarding alias must be unique.",
    )

    @api.depends(
        "progress_ids", "progress_ids.company_id", "step_ids", "step_ids.is_per_company"
    )
    def _compute_is_per_company(self):
        # Once an onboarding is made "per-company", there is no drawback to simply still consider
        # it per-company even when if its last per-company step is unlinked. This allows to avoid
        # handling the merging of existing progress (step) records.

        onboardings_with_per_company_steps_or_progress = self.filtered(
            lambda o: (
                o.progress_ids.company_id
                or (True in o.step_ids.mapped("is_per_company"))
            )
        )
        onboardings_with_per_company_steps_or_progress.is_per_company = True
        (self - onboardings_with_per_company_steps_or_progress).is_per_company = False

    @api.depends_context("company")
    @api.depends(
        "progress_ids",
        "progress_ids.is_onboarding_closed",
        "progress_ids.onboarding_state",
        "progress_ids.company_id",
    )
    def _compute_current_progress(self):
        for onboarding in self:
            current_progress_id = onboarding.progress_ids.filtered(
                lambda progress: progress.company_id.id in {False, self.env.company.id}
            )
            if current_progress_id:
                onboarding.current_onboarding_state = (
                    current_progress_id.onboarding_state
                )
                onboarding.current_progress_id = current_progress_id
                onboarding.is_onboarding_closed = (
                    current_progress_id.is_onboarding_closed
                )
            else:
                onboarding.current_onboarding_state = "not_done"
                onboarding.current_progress_id = False
                onboarding.is_onboarding_closed = False

    def write(self, vals):
        """Recompute progress step ids if new steps are added/removed."""
        already_linked_steps_by_id = {
            onboarding.id: onboarding.step_ids for onboarding in self
        }
        res = super().write(vals)
        changed = self.filtered(
            lambda onboarding: (
                onboarding.step_ids != already_linked_steps_by_id[onboarding.id]
            )
        )
        if changed:
            # Split progress into per-company records if `step_ids` made `changed` become
            # per-company (mirrors the same repair triggered from the step side in
            # `onboarding.onboarding.step.write()`).
            changed.action_refresh_progress_ids()
            changed.progress_ids._recompute_progress_step_ids()
        return res

    def action_close(self):
        """Close the onboarding panel."""
        self.current_progress_id.action_close()

    @api.model
    def action_close_panel(self, xmlid):
        """Close the onboarding panel identified by its `xmlid`.

        If not found, quietly do nothing.
        """
        if onboarding := self.env.ref(xmlid, raise_if_not_found=False):
            onboarding.action_close()

    def action_refresh_progress_ids(self):
        """Re-initialize onboarding progress records (after step is_per_company change).

        Meant to be called when `is_per_company` of linked steps is modified (or per-company
        steps are added to an onboarding).
        """
        onboardings_to_refresh_progress = self.filtered(
            lambda o: (
                o.is_per_company and o.progress_ids and not o.progress_ids.company_id
            )
        )
        onboardings_to_refresh_progress.progress_ids.unlink()
        onboardings_to_refresh_progress._create_progress()

    def action_toggle_visibility(self):
        self.current_progress_id.action_toggle_visibility()

    def _search_or_create_progress(self):
        """Create Progress record(s) as necessary for the context."""
        onboardings_without_progress = self.filtered(
            lambda onboarding: not onboarding.current_progress_id
        )
        onboardings_without_progress._create_progress()
        return self.current_progress_id

    def _create_progress(self):
        return self.env["onboarding.progress"].create(
            [
                {
                    "company_id": self.env.company.id
                    if onboarding.is_per_company
                    else False,
                    "onboarding_id": onboarding.id,
                    "progress_step_ids": onboarding.step_ids.progress_ids.filtered(
                        lambda p: p.company_id.id in [False, self.env.company.id]
                    ),
                }
                for onboarding in self
            ]
        )

    def _prepare_rendering_values(self):
        self.check_singleton()
        return {
            "close_method": self.panel_close_action_name,
            "close_model": "onboarding.onboarding",
            "steps": self.step_ids,
            "state": self.current_progress_id._get_and_update_onboarding_state(),
            "text_completed": self.text_completed,
        }
