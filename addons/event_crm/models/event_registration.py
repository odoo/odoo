from markupsafe import Markup

from odoo import Command, _, api, fields, models, tools


class EventRegistration(models.Model):
    _inherit = "event.registration"

    lead_ids = fields.Many2many(
        comodel_name="crm.lead",
        string="Leads",
        copy=False,
        readonly=True,
        groups="sale.group_sale_salesman",
    )
    lead_count = fields.Count(
        count_of="lead_ids",
        string="# Leads",
        compute_sudo=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        registrations = super().create(vals_list)

        if not self.env.context.get("event_lead_rule_skip"):
            registrations._apply_lead_generation_rules()
        return registrations

    def write(self, vals):
        to_update, event_lead_rule_skip = (
            False,
            self.env.context.get("event_lead_rule_skip"),
        )
        if not event_lead_rule_skip:
            to_update = self.filtered(lambda reg: reg.lead_count)
        if to_update:
            lead_tracked_vals = to_update._get_lead_tracked_values()

        res = super().write(vals)

        if not event_lead_rule_skip and to_update:
            self.env.flush_all()
            to_update.sudo()._update_leads(vals, lead_tracked_vals)

        if not event_lead_rule_skip:
            if vals.get("state") == "open":
                self.env["event.lead.rule"].search(
                    [("lead_creation_trigger", "=", "confirm")]
                ).sudo()._run_on_registrations(self)
            elif vals.get("state") == "done":
                self.env["event.lead.rule"].search(
                    [("lead_creation_trigger", "=", "done")]
                ).sudo()._run_on_registrations(self)

        return res

    def _load_records_create(self, values):
        return super(
            EventRegistration, self.with_context(event_lead_rule_skip=True)
        )._load_records_create(values)

    def _load_records_write(self, values):
        return super(
            EventRegistration, self.with_context(event_lead_rule_skip=True)
        )._load_records_write(values)

    def _apply_lead_generation_rules(self, event_lead_rules=False):
        leads = self.env["crm.lead"]
        open_registrations = self.filtered(lambda reg: reg.state == "open")
        done_registrations = self.filtered(lambda reg: reg.state == "done")

        if not event_lead_rules:
            search_triggers = ["create"]
            if open_registrations:
                search_triggers.append("confirm")
            if done_registrations:
                search_triggers.append("done")
            event_lead_rules = self.env["event.lead.rule"].search(
                [("lead_creation_trigger", "in", search_triggers)]
            )

        create_lead_rules = event_lead_rules.filtered(
            lambda rule: rule.lead_creation_trigger == "create"
        )
        leads += create_lead_rules.sudo()._run_on_registrations(self)
        if open_registrations:
            confirm_lead_rules = event_lead_rules.filtered(
                lambda rule: rule.lead_creation_trigger == "confirm"
            )
            leads += confirm_lead_rules.sudo()._run_on_registrations(open_registrations)
        if done_registrations:
            done_lead_rules = event_lead_rules.filtered(
                lambda rule: rule.lead_creation_trigger == "done"
            )
            leads += done_lead_rules.sudo()._run_on_registrations(done_registrations)
        return leads

    def _update_leads(self, new_vals, lead_tracked_vals):
        for registration in self:
            leads_attendee = registration.lead_ids.filtered(
                lambda lead: lead.event_lead_rule_id.lead_creation_basis == "attendee"
            )
            if not leads_attendee:
                continue

            old_vals = lead_tracked_vals[registration.id]
            if "partner_id" in new_vals:
                new_vals.update(
                    **{
                        field: registration[field]
                        for field in self._get_fields_lead_contact()
                        if field != "partner_id"
                    }
                )

            lead_values = {}
            upd_contact_fields = [
                field for field in self._get_fields_lead_contact() if field in new_vals
            ]
            if any(new_vals[field] != old_vals[field] for field in upd_contact_fields):
                lead_values = registration._prepare_lead_contact_vals()

            upd_description_fields = [
                field
                for field in self._get_fields_lead_description()
                if field in new_vals
            ]
            if any(
                new_vals[field] != old_vals[field] for field in upd_description_fields
            ):
                for lead in leads_attendee:
                    lead_values["description"] = "%s<br/>%s" % (
                        lead.description,
                        registration._get_lead_description(
                            _("Updated registrations"), line_counter=True
                        ),
                    )
                    lead.write(lead_values)
            elif lead_values:
                leads_attendee.write(lead_values)

        leads_order = self.lead_ids.filtered(
            lambda lead: lead.event_lead_rule_id.lead_creation_basis == "order"
        )
        for lead in leads_order:
            lead_values = {}
            if new_vals.get("partner_id"):
                lead_values.update(lead.registration_ids._prepare_lead_contact_vals())
                if not lead.partner_id:
                    lead_values["description"] = (
                        lead.registration_ids._get_lead_description(
                            _("Participants"), line_counter=True
                        )
                    )
                elif new_vals["partner_id"] != lead.partner_id.id:
                    lead_values["description"] = (
                        (lead.description or "")
                        + "<br/>"
                        + lead.registration_ids._get_lead_description(
                            _("Updated registrations"),
                            line_counter=True,
                            line_suffix=_("(updated)"),
                        )
                    )
            if lead_values:
                lead.write(lead_values)

    def _prepare_lead_vals(self, rule):
        sorted_self = self.sorted("id")
        lead_values = {
            "type": rule.lead_type,
            "user_id": rule.lead_user_id.id,
            "team_id": rule.lead_sales_team_id.id,
            "tag_ids": rule.lead_tag_ids.ids,
            "event_lead_rule_id": rule.id,
            "event_id": self.event_id.id,
            "referred": self.event_id.name,
            "registration_ids": self.ids,
            "campaign_id": sorted_self._find_first_notnull("utm_campaign_id"),
            "source_id": sorted_self._find_first_notnull("utm_source_id"),
            "medium_id": sorted_self._find_first_notnull("utm_medium_id"),
        }
        lead_values.update(sorted_self._prepare_lead_contact_vals())
        lead_values["description"] = sorted_self._get_lead_description(
            _("Participants"), line_counter=True
        )
        return lead_values

    def _prepare_lead_contact_vals(self):
        sorted_self = self.sorted("id")
        valid_partner = next(
            (
                reg.partner_id
                for reg in sorted_self
                if reg.partner_id != self.env.ref("base.public_partner")
            ),
            self.env["res.partner"],
        )

        if len(self) == 1 and valid_partner:
            if self.email and valid_partner.email:
                if (
                    valid_partner.email_normalized
                    and tools.email_normalize(self.email)
                    != valid_partner.email_normalized
                ) or (
                    not valid_partner.email_normalized
                    and valid_partner.email != self.email
                ):
                    valid_partner = self.env["res.partner"]

            if (
                valid_partner
                and self.phone_ids
                and valid_partner.phone_ids
                and not set(self.phone_ids.mapped("sanitized"))
                & set(valid_partner.phone_ids.mapped("sanitized"))
            ):
                valid_partner = self.env["res.partner"]

        registration_phone_ids = sorted_self._find_first_notnull("phone_ids")
        registration_phone_command = (
            [Command.set(registration_phone_ids)] if registration_phone_ids else False
        )
        if valid_partner:
            contact_vals = self.env["crm.lead"]._prepare_values_from_partner(
                valid_partner
            )
            if not valid_partner.email:
                contact_vals["email_from"] = sorted_self._find_first_notnull("email")
            if not valid_partner.phone_ids:
                contact_vals["phone_ids"] = registration_phone_command
        else:
            contact_vals = {
                "contact_name": sorted_self._find_first_notnull("name"),
                "email_from": sorted_self._find_first_notnull("email"),
                "phone_ids": registration_phone_command,
                "lang_id": False,
            }
        contact_name = (
            valid_partner.name
            or sorted_self._find_first_notnull("name")
            or sorted_self._find_first_notnull("email")
        )
        contact_vals.update(
            {
                "name": f"{self.event_id[:1].name} - {contact_name}",
                "partner_id": valid_partner.id,
            }
        )

        return contact_vals

    def _get_lead_description(self, prefix="", line_counter=True, line_suffix=""):
        reg_lines = [
            registration._get_lead_description_registration(line_suffix=line_suffix)
            for registration in self
        ]
        description = (prefix or "") + Markup("<br/>")
        if line_counter:
            description += Markup("<ol>") + Markup("").join(reg_lines) + Markup("</ol>")
        else:
            description += Markup("<ul>") + Markup("").join(reg_lines) + Markup("</ul>")
        return description

    def _get_lead_description_registration(self, line_suffix=""):
        self.check_singleton()
        return (
            Markup("<li>")
            + "%s (%s)%s"
            % (
                self.name or self.partner_id.name or self.email,
                " - ".join(
                    value
                    for value in (self.email, self._phone_get_number().number)
                    if value
                ),
                f" {line_suffix}" if line_suffix else "",
            )
            + Markup("</li>")
        )

    def _get_lead_tracked_values(self):
        tracked_fields = list(
            set(self._get_fields_lead_contact())
            | set(self._get_fields_lead_description())
        )
        return {
            registration.id: {
                field: self._convert_value(registration[field], field)
                for field in tracked_fields
            }
            for registration in self
        }

    def _get_lead_grouping(self, rules, rule_to_new_regs):
        grouped_registrations = {
            (create_date, event): sub_registrations
            for event, registrations in self.grouped("event_id").items()
            for create_date, sub_registrations in registrations.grouped(
                "create_date"
            ).items()
        }

        return {
            rule: [
                (False, key, (registrations & rule_to_new_regs[rule]).sorted("id"))
                for key, registrations in grouped_registrations.items()
            ]
            for rule in rules
        }

    @api.model
    def _get_fields_lead_contact(self):
        return ["name", "email", "phone_ids", "partner_id"]

    @api.model
    def _get_fields_lead_description(self):
        return ["name", "email", "phone_ids"]

    def _find_first_notnull(self, field_name):
        value = next((reg[field_name] for reg in self if reg[field_name]), False)
        return self._convert_value(value, field_name)

    def _convert_value(self, value, field_name):
        if isinstance(value, models.BaseModel) and self._fields[field_name].type in [
            "many2many",
            "one2many",
        ]:
            return value.ids
        if (
            isinstance(value, models.BaseModel)
            and self._fields[field_name].type == "many2one"
        ):
            return value.id
        return value
