from markupsafe import Markup

from odoo import _, fields, models
from odoo.tools.misc import file_open


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    mass_mailing_id = fields.Many2one(
        comodel_name="mailing.mailing",
        ondelete="cascade",
    )
    campaign_id = fields.Many2one(
        comodel_name="utm.campaign",
        string="Mass Mailing Campaign",
        ondelete="set null",
    )
    mass_mailing_name = fields.Char(
        help="If set, a mass mailing will be created so that you can track its results in the Email Marketing app."
    )
    mailing_list_ids = fields.Many2many(comodel_name="mailing.list")

    def _get_render_error_label(self):
        """Name the mailing, not the transient composer that renders for it.

        Lived in `mixin.mail.render` as a `self._name == "mail.compose.message"`
        branch guarded by `"mass_mailing_id" in self._fields` -- the mixin
        testing for a field this module adds.
        """
        if not self.mass_mailing_id:
            return super()._get_render_error_label()
        return _(
            "Mass Mailing Template: '%(name)s' (ID: %(record_id)s)",
            name=self.mass_mailing_id.display_name or _("Unnamed Mailing"),
            record_id=self.mass_mailing_id.id,
        )

    def _action_send_mail(self, auto_commit=False):
        """Override to generate the mass mailing in case only the name was
        given. It is used afterwards for traces generation."""
        if (
            self.composition_mode == "mass_mail"
            and self.mass_mailing_name
            and not self.mass_mailing_id
            and self.model_is_thread
        ):
            mass_mailing = self.env["mailing.mailing"].create(
                self._prepare_mailing_values()
            )
            self.mass_mailing_id = mass_mailing.id
        return super()._action_send_mail(auto_commit=auto_commit)

    def _invalid_email_state(self):
        """Always cancel invalid emails for mailings due to likely untractable number of failures."""
        if self.mass_mailing_name or self.mass_mailing_id:
            return "cancel"
        return super()._invalid_email_state()

    def _generate_mail_notification_values(self, mails):
        """Prevent notification creation as traces are generated."""
        if self.mass_mailing_name or self.mass_mailing_id:
            return []
        return super()._generate_mail_notification_values(mails)

    def _wrap_bodies_in_mailing_layout(self, mail_values_all):
        """Put every recipient's body inside the mailing layout, in one pass.

        Only ``body`` differs between recipients — the stylesheet is the same
        file for all of them — so this was `ir.qweb._render` once per recipient
        with a values dict that changed in one key. Measured over a 500-recipient
        send, that was 78ms of a 1043ms generation, and the whole of it was the
        preparation `_render` redoes on every call.
        """
        with file_open(
            "mass_mailing/static/src/scss/mass_mailing_mail.scss", "r"
        ) as fd:
            styles = fd.read()
        with_body = [
            res_id
            for res_id, mail_values in mail_values_all.items()
            if mail_values.get("body_html")
        ]
        if not with_body:
            return
        bodies = self.env["ir.qweb"]._render_batch(
            "mass_mailing.mass_mailing_mail_layout",
            {"mailing_style": Markup(f"<style>{styles}</style>")},
            ({"body": mail_values_all[res_id]["body_html"]} for res_id in with_body),
            minimal_qcontext=True,
            raise_if_not_found=False,
        )
        for res_id, body in zip(with_body, bodies, strict=True):
            # A missing layout renders empty; the body it was given stands.
            if body:
                mail_values_all[res_id]["body_html"] = body

    def _prepare_mail_values(self, res_ids):
        # When being in mass mailing mode, add 'mailing.trace' values directly in the o2m field of mail.mail.
        mail_values_all = super()._prepare_mail_values(res_ids)

        if not self._is_mass_mailing():
            return mail_values_all

        trace_values_all = self._prepare_mail_values_mailing_traces(mail_values_all)
        self._wrap_bodies_in_mailing_layout(mail_values_all)
        for res_id, mail_values in mail_values_all.items():
            if mail_values.get("body"):
                mail_values["body"] = Markup(
                    "<div><span>{mailing_sent_message}</span></div>"
                    '<blockquote class="border-start" data-o-mail-quote="1" data-o-mail-quote-node="1">'
                    "{original_body}"
                    "</blockquote>"
                ).format(
                    mailing_sent_message=Markup(
                        _(
                            "Received the mailing <b>{mailing_name}</b>",
                        )
                    ).format(
                        mailing_name=self.mass_mailing_name
                        or self.mass_mailing_id.display_name
                    ),
                    original_body=mail_values["body"],
                )

            mail_values.update(
                {
                    "mailing_id": self.mass_mailing_id.id,
                    "mailing_trace_ids": [(0, 0, trace_values_all[res_id])]
                    if res_id in trace_values_all
                    else False,
                }
            )
        return mail_values_all

    def _get_done_emails(self, mail_values_dict):
        seen_list = super()._get_done_emails(mail_values_dict)
        if self.mass_mailing_id:
            seen_list += self.mass_mailing_id._get_seen_list()
        return seen_list

    def _get_optout_emails(self, mail_values_dict):
        opt_out_list = super()._get_optout_emails(mail_values_dict)
        if self.mass_mailing_id:
            opt_out_list += self.mass_mailing_id._get_opt_out_list()
        return opt_out_list

    def _prepare_mail_values_mailing_traces(self, mail_values_all):
        trace_values_all = dict.fromkeys(mail_values_all.keys(), False)
        recipients_info = self._get_recipients_data(mail_values_all)
        for res_id, mail_values in mail_values_all.items():
            emails = recipients_info[res_id]["mail_to_normalized"]
            # if mail_to is void, keep falsy values to allow searching / debugging traces
            if not emails:
                emails = recipients_info[res_id]["mail_to"]
            email = emails[0] if emails else ""
            trace_vals = {
                "email": email,
                "mass_mailing_id": self.mass_mailing_id.id,
                "message_id": mail_values["message_id"],
                "model": self.model,
                "res_id": res_id,
            }
            # propagate failed states to trace when still-born
            if mail_values.get("state") == "cancel":
                trace_vals["trace_status"] = "cancel"
            elif mail_values.get("state") == "exception":
                trace_vals["trace_status"] = "error"
            if mail_values.get("failure_type"):
                trace_vals["failure_type"] = mail_values["failure_type"]
            trace_values_all[res_id] = trace_vals
        return trace_values_all

    def _prepare_mailing_values(self):
        now = fields.Datetime.now()
        return {
            "attachment_ids": [(6, 0, self.attachment_ids.ids)],
            "body_html": self.body,
            "campaign_id": self.campaign_id.id,
            "mailing_model_id": self.env["ir.model"]._get(self.model).id,
            "mailing_domain": self.res_domain or f"[('id', 'in', {self.res_ids})]",
            "name": self.mass_mailing_name,
            "reply_to": self.reply_to if self.reply_to_mode == "new" else False,
            "reply_to_mode": self.reply_to_mode,
            "sent_date": now,
            "state": "done",
            "subject": self.subject,
            "use_exclusion_list": self.use_exclusion_list,
        }

    def _manage_mail_values(self, mail_values_all):
        # Filter out canceled messages of mass mailing and create traces for canceled ones.
        results = super()._manage_mail_values(mail_values_all)
        if not self._is_mass_mailing():
            return results
        self.env["mailing.trace"].sudo().create(
            [
                trace_commands[0][2]
                for mail_values in results.values()
                if (
                    mail_values.get("state") == "cancel"
                    and (trace_commands := mail_values["mailing_trace_ids"])
                    # Ensure it is a create command
                    and len(trace_commands) == 1
                    and len(trace_commands[0]) == 3
                    and trace_commands[0][0] == 0
                )
            ]
        )
        return {
            res_id: mail_values
            for res_id, mail_values in results.items()
            if mail_values.get("state") != "cancel"
        }

    def _is_mass_mailing(self):
        # allowed models in mass mailing
        return (
            self.composition_mode == "mass_mail"
            and self.mass_mailing_id
            and self.model_is_thread
        )
