import logging
from collections import defaultdict

from markupsafe import Markup

from odoo import Command, _, api, models, modules, tools
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog

from odoo.addons.web.models.ir_actions_report import PDF_OPTIONS_DATA_KEY

_logger = logging.getLogger(__name__)

_debug = DebugLog(__name__)


class MixinAccountMoveSend(models.AbstractModel):
    _name = "mixin.account.move.send"
    _description = "Account Move Send"

    @api.model
    def _get_default_sending_methods(self, move) -> set:
        return {
            move.commercial_partner_id.with_company(
                move.company_id
            ).invoice_sending_method
            or "email"
        }

    @api.model
    def _get_all_extra_edis(self) -> dict:
        return {}

    @api.model
    def _get_default_extra_edis(self, move) -> set:
        extra_edis = self._get_all_extra_edis()
        return {
            edi_key
            for edi_key, edi_vals in extra_edis.items()
            if edi_vals["is_applicable"](move)
        }

    @api.model
    def _get_default_invoice_edi_format(self, move, **kwargs) -> str:
        return move.commercial_partner_id.with_company(
            move.company_id
        ).invoice_edi_format

    @api.model
    def _get_default_pdf_report_id(self, move):
        if partner_default_template := move.commercial_partner_id.with_company(
            move.company_id
        ).invoice_template_pdf_report_id:
            _debug.logic("pdf_report_chosen", move=move, source="partner")
            return partner_default_template

        if journal_default_template := move.journal_id.with_company(
            move.company_id
        ).invoice_template_pdf_report_id:
            _debug.logic("pdf_report_chosen", move=move, source="journal")
            return journal_default_template

        action_report = self.env.ref("account.account_invoices")

        if move._is_action_report_available(action_report):
            _debug.logic("pdf_report_chosen", move=move, source="default_action")
            return action_report

        _debug.logic("pdf_report_missing", move=move)
        raise UserError(_("There is no template that applies to this move type."))

    @api.model
    def _get_default_mail_template_id(self, move):
        return move._get_mail_template()

    def _get_default_mail_sending_settings(self, move, get_setting, mail_template):
        mail_lang = get_setting("mail_lang") or self._get_default_mail_lang(
            move, mail_template
        )
        return {
            "mail_template": mail_template,
            "mail_lang": mail_lang,
            "mail_body": get_setting(
                "mail_body",
                default_value=self._get_default_mail_body(
                    move, mail_template, mail_lang
                ),
            ),
            "mail_subject": get_setting(
                "mail_subject",
                default_value=self._get_default_mail_subject(
                    move, mail_template, mail_lang
                ),
            ),
            "mail_partner_ids": get_setting(
                "mail_partner_ids",
                default_value=self._get_default_mail_partner_ids(
                    move, mail_template, mail_lang
                ).ids,
            ),
            "reply_to": get_setting("reply_to")
            or self._get_mail_default_field_value_from_template(
                mail_template, mail_lang, move, "reply_to"
            ),
        }

    @api.model
    @_debug.perf.timed
    def _get_default_sending_settings(self, move, from_cron=False, **custom_settings):
        def get_setting(key, from_cron=False, default_value=None):
            return (
                custom_settings.get(key)
                if key in custom_settings
                else move.sending_data.get(key)
                if from_cron
                else default_value
            )

        vals = {
            "sending_methods": get_setting(
                "sending_methods", default_value=self._get_default_sending_methods(move)
            )
            or {},
            "extra_edis": get_setting(
                "extra_edis", default_value=self._get_default_extra_edis(move)
            )
            or {},
            "pdf_report": get_setting("pdf_report")
            or self._get_default_pdf_report_id(move),
            "author_user_id": get_setting("author_user_id", from_cron=from_cron)
            or self.env.user.id,
            "author_partner_id": get_setting("author_partner_id", from_cron=from_cron)
            or self.env.user.partner_id.id,
        }
        vals["invoice_edi_format"] = get_setting(
            "invoice_edi_format",
            default_value=self._get_default_invoice_edi_format(
                move, sending_methods=vals["sending_methods"]
            ),
        )
        mail_template = get_setting(
            "mail_template"
        ) or self._get_default_mail_template_id(move)
        if "email" in vals["sending_methods"]:
            vals.update(
                self._get_default_mail_sending_settings(
                    move, get_setting, mail_template
                )
            )
        if self._display_attachments_widget(
            vals["invoice_edi_format"], vals["sending_methods"]
        ):
            mail_attachments_widget = self._prepare_mail_attachments_widget(
                move,
                mail_template,
                invoice_edi_format=vals["invoice_edi_format"],
                extra_edis=vals["extra_edis"],
                pdf_report=vals["pdf_report"],
            )
            vals["mail_attachments_widget"] = get_setting(
                "mail_attachments_widget", default_value=mail_attachments_widget
            )
        _debug.logic(
            "send_settings",
            move=move,
            methods=vals["sending_methods"],
            edis=vals["extra_edis"],
            edi_format=vals["invoice_edi_format"],
            pdf_report=vals["pdf_report"],
            template=mail_template,
            from_cron=from_cron,
            custom=sorted(custom_settings),
        )
        return vals

    @api.model
    @_debug.perf.timed
    def _get_alerts(self, moves, moves_data):
        alerts = {}
        send_cron = self.env.ref(
            "account.ir_cron_account_move_send", raise_if_not_found=False
        )
        if len(moves) > 1 and send_cron and not send_cron.sudo().active:
            has_cron_access = send_cron.has_access("write")
            has_access_message = _(
                "The scheduled action 'Send Invoices automatically' is archived. You won't be able to send invoices in batch."
            )
            no_access_addendum = _("\nPlease contact your administrator.")
            alerts["account_send_cron_archived"] = {
                "level": "warning",
                "message": has_access_message
                if has_cron_access
                else has_access_message + no_access_addendum,
                "action_text": _("Check") if has_cron_access else None,
                "action": send_cron._get_records_action() if has_cron_access else None,
            }
        email_moves = moves.filtered(
            lambda m: "email" in moves_data[m]["sending_methods"]
        )
        if email_moves:
            if is_batch := len(moves) > 1:
                partners_without_mail = email_moves.filtered(
                    lambda m: not m.partner_id.email
                ).mapped("partner_id")
            else:
                mail_partners = moves_data[email_moves]["mail_partner_ids"]
                if not isinstance(mail_partners, models.BaseModel):
                    mail_partners = self.env["res.partner"].browse(mail_partners)
                partners_without_mail = mail_partners.filtered(lambda p: not p.email)

            if partners_without_mail:
                alerts["account_missing_email"] = {
                    "level": "warning" if is_batch else "danger",
                    "message": _("Partner(s) should have an email address."),
                    "action_text": _("View Partner(s)") if is_batch else False,
                    "action": (
                        partners_without_mail._get_records_action(
                            name=_("Check Partner(s) Email(s)")
                        )
                        if is_batch
                        else False
                    ),
                }

        if _debug.logic.enabled:
            _debug.logic(
                "send_alerts_built",
                move=moves,
                email_moves=len(email_moves),
                alerts=sorted(alerts),
            )
        return alerts

    @api.model
    def _get_mail_default_field_value_from_template(
        self, mail_template, lang, move, field, **kwargs
    ):
        if not mail_template:
            return None
        return (
            mail_template.sudo()
            .with_context(lang=lang)
            ._render_field(field, move.ids, **kwargs)[move._origin.id]
        )

    @api.model
    def _get_default_mail_lang(self, move, mail_template):
        return mail_template._render_lang([move.id]).get(move.id)

    @api.model
    def _get_default_mail_body(self, move, mail_template, mail_lang):
        return self._get_mail_default_field_value_from_template(
            mail_template,
            mail_lang,
            move,
            "body_html",
            options={"post_process": True},
        )

    @api.model
    def _get_default_mail_subject(self, move, mail_template, mail_lang):
        return self._get_mail_default_field_value_from_template(
            mail_template,
            mail_lang,
            move,
            "subject",
        )

    @api.model
    @_debug.perf.timed
    def _get_default_mail_partner_ids(self, move, mail_template, mail_lang):
        partners = self.env["res.partner"].with_company(move.company_id)
        if mail_template.use_default_to:
            defaults = move._message_get_default_recipients()[move.id]
            email_cc = ""
            email_to = defaults["email_to"]
            partners |= partners.browse(defaults["partner_ids"])
        else:
            if mail_template.email_cc:
                email_cc = self._get_mail_default_field_value_from_template(
                    mail_template, mail_lang, move, "email_cc"
                )
            else:
                email_cc = ""
            if mail_template.email_to:
                email_to = self._get_mail_default_field_value_from_template(
                    mail_template, mail_lang, move, "email_to"
                )
            else:
                email_to = ""

        partners |= move._partner_get_or_create_from_emails_single(
            tools.email_split(email_cc or "") + tools.email_split(email_to or ""),
            no_create=False,
        )

        if not mail_template.use_default_to and mail_template.partner_to:
            partner_to = self._get_mail_default_field_value_from_template(
                mail_template, mail_lang, move, "partner_to"
            )
            partner_ids = mail_template._parse_partner_to(partner_to)
            partners |= self.env["res.partner"].sudo().browse(partner_ids).exists()
        _debug.logic(
            "mail_recipients_resolved",
            move=move,
            template=mail_template,
            use_default_to=mail_template.use_default_to,
            candidates=len(partners),
            allow_without_mail=bool(
                self.env.context.get("allow_partners_without_mail")
            ),
        )
        return (
            partners
            if self.env.context.get("allow_partners_without_mail")
            else partners.filtered("email")
        )

    @api.model
    def _prepare_mail_attachments_widget(
        self,
        move,
        mail_template,
        invoice_edi_format=None,
        extra_edis=None,
        pdf_report=None,
    ):
        return (
            self._prepare_mail_attachment_placeholders(
                move,
                invoice_edi_format=invoice_edi_format,
                extra_edis=extra_edis,
                pdf_report=pdf_report,
            )
            + self._prepare_dynamic_mail_attachment_placeholders(
                move, mail_template, pdf_report=pdf_report
            )
            + self._prepare_invoice_attachment_entries(move)
            + self._prepare_template_attachment_entries(mail_template)
        )

    @api.model
    def _prepare_mail_attachment_placeholders(
        self, move, invoice_edi_format=None, extra_edis=None, pdf_report=None
    ):
        if move.invoice_pdf_report_id:
            return []
        filename = move._get_invoice_report_filename(report=pdf_report)
        return [
            {
                "id": f"placeholder_{filename}",
                "name": filename,
                "mimetype": "application/pdf",
                "placeholder": True,
            }
        ]

    @api.model
    def _prepare_dynamic_mail_attachment_placeholders(
        self, move, mail_template, pdf_report=None
    ):
        pdf_report = pdf_report or self._get_default_pdf_report_id(move)
        invoice_template = pdf_report | self.env.ref("account.account_invoices")
        extra_mail_templates = mail_template.report_template_ids - invoice_template
        attachments = []
        for extra_mail_template in extra_mail_templates:
            if extra_mail_template.print_report_name:
                filename = move._get_invoice_mail_template_dynamic_report_filename(
                    report=extra_mail_template
                )
            else:
                filename = f"{extra_mail_template.name.lower()}_{move.name}.pdf"
            attachments.append(
                {
                    "id": f"placeholder_{extra_mail_template.name.lower()}_{filename}",
                    "name": filename,
                    "mimetype": "application/pdf",
                    "placeholder": True,
                    "dynamic_report": extra_mail_template.report_name,
                }
            )
        return attachments

    @api.model
    def _get_invoice_extra_attachments(self, move):
        return move.invoice_pdf_report_id

    @api.model
    def _prepare_invoice_attachment_entries(self, move):
        return [
            {
                "id": attachment.id,
                "name": attachment.name,
                "mimetype": attachment.mimetype,
                "placeholder": False,
                "protect_from_deletion": True,
            }
            for attachment in self._get_invoice_extra_attachments(move)
        ]

    @api.model
    def _prepare_template_attachment_entries(self, mail_template):
        return [
            {
                "id": attachment.id,
                "name": attachment.name,
                "mimetype": attachment.mimetype,
                "placeholder": False,
                "mail_template_id": mail_template.id,
                "protect_from_deletion": True,
            }
            for attachment in mail_template.attachment_ids
        ]

    @api.model
    def _raise_danger_alerts(self, alerts):
        danger_alert_messages = [
            alert["message"]
            for alert in alerts.values()
            if alert.get("level") == "danger"
        ]
        if danger_alert_messages:
            raise UserError("\n".join(danger_alert_messages))

    @api.model
    @_debug.perf.timed
    def _check_move_constraints(self, moves):
        errors = []
        for move in moves:
            if move_constraints := self._get_move_constraints(move):
                _debug.logic("send_refused", move=move, fields=sorted(move_constraints))
                message = next(iter(move_constraints.values()), None)
                errors.append(f"{move.display_name}: {message}")
        if errors:
            raise UserError("\n".join(errors))

    @api.model
    def _get_move_constraints(self, move):
        constraints = {}
        if move.state != "posted":
            constraints["not_posted"] = _(
                "You can't generate invoices that are not posted."
            )
        is_self_billing = move.journal_id.is_self_billing and move.is_purchase_document(
            include_receipts=True
        )
        if not move.is_sale_document(include_receipts=True) and not is_self_billing:
            constraints["not_sale_document"] = _(
                "You can only generate sales documents."
            )
        return constraints

    @api.model
    @_debug.perf.timed
    def _check_invoice_report(self, moves, **custom_settings):
        if (
            custom_settings.get("pdf_report")
            and any(
                not move._is_action_report_available(custom_settings["pdf_report"])
                for move in moves
            )
        ) or any(
            not self._get_default_pdf_report_id(move).is_invoice_report
            for move in moves
        ):
            raise UserError(
                _(
                    "The sending of invoices is not set up properly, make sure the report used is set for invoices."
                )
            )

    @api.model
    def _normalize_error(self, error):
        if not isinstance(error, dict):
            return {"error_title": str(error)}
        return error

    @api.model
    def _format_error_text(self, error):
        error = self._normalize_error(error)
        errors = "\n- ".join(error.get("errors", ""))
        return f"{error['error_title']}\n- {errors}" if errors else error["error_title"]

    @api.model
    def _format_error_html(self, error):
        error = self._normalize_error(error)
        if "errors" not in error:
            return error["error_title"]
        errors = Markup().join(
            Markup("<li>%s</li>") % error for error in error["errors"]
        )
        return Markup("%s<ul>%s</ul>") % (error["error_title"], errors)

    @api.model
    def _display_attachments_widget(self, edi_format, sending_methods):
        return "email" in sending_methods

    @api.model
    def _is_applicable_to_company(self, method, company):
        return True

    @api.model
    def _is_applicable_to_move(self, method, move, **move_data):
        if method == "email" and "mail_partner_ids" in move_data:
            return bool(move_data["mail_partner_ids"])
        return True

    @api.model
    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        return

    @api.model
    @_debug.perf.timed
    def _update_invoice_data_pdf_report(self, invoices_data):
        grouped_invoices_by_report = defaultdict(dict)
        for invoice, invoice_data in invoices_data.items():
            grouped_invoices_by_report[
                (invoice.company_id, invoice_data["pdf_report"])
            ][invoice] = invoice_data

        _debug.pipeline(
            "pdf_report_groups_built",
            invoices=len(invoices_data),
            groups=len(grouped_invoices_by_report),
        )
        for (
            company,
            pdf_report,
        ), group_invoices_data in grouped_invoices_by_report.items():
            Report = self.env["ir.actions.report"].with_company(company)
            ids = [inv.id for inv in group_invoices_data]

            render_options = {
                invoice: self._get_invoice_pdf_render_options(invoice, invoice_data)
                for invoice, invoice_data in group_invoices_data.items()
            }
            if _debug.logic.enabled:
                _debug.logic(
                    "pdf_render_mode_chosen",
                    company=company,
                    report=pdf_report,
                    invoices=len(ids),
                    per_invoice=any(render_options.values()),
                )
            if any(render_options.values()):
                content_by_id = {}
                for invoice in group_invoices_data:
                    content, report_type = Report._pre_render_qweb_pdf(
                        pdf_report.report_name,
                        res_ids=[invoice.id],
                        data={PDF_OPTIONS_DATA_KEY: render_options[invoice]}
                        if render_options[invoice]
                        else None,
                    )
                    splitted_report = self.env[
                        "ir.actions.report"
                    ]._get_splitted_report(pdf_report.report_name, content, report_type)
                    if invoice.id not in splitted_report:
                        raise ValidationError(
                            _(
                                "Cannot identify the invoices in the generated PDF: %s",
                                invoice.ids,
                            )
                        )
                    content_by_id.update(splitted_report)
            else:
                content, report_type = Report._pre_render_qweb_pdf(
                    pdf_report.report_name, res_ids=ids
                )
                content_by_id = self.env["ir.actions.report"]._get_splitted_report(
                    pdf_report.report_name, content, report_type
                )
                if len(content_by_id) == 1 and False in content_by_id:
                    raise ValidationError(
                        _("Cannot identify the invoices in the generated PDF: %s", ids)
                    )

            for invoice, invoice_data in group_invoices_data.items():
                invoice_data["pdf_attachment_values"] = {
                    "name": invoice._get_invoice_report_filename(report=pdf_report),
                    "raw": content_by_id[invoice.id],
                    "mimetype": "application/pdf",
                    "res_model": invoice._name,
                    "res_id": invoice.id,
                    "res_field": "invoice_pdf_report_file",
                }

    @api.model
    def _get_invoice_pdf_render_options(self, invoice, invoice_data):
        return {}

    @api.model
    def _update_invoice_data_proforma_pdf_report(self, invoice, invoice_data):
        pdf_report = invoice_data["pdf_report"]
        content, report_type = (
            self.env["ir.actions.report"]
            .with_company(invoice.company_id)
            ._pre_render_qweb_pdf(
                pdf_report.report_name, invoice.ids, data={"proforma": True}
            )
        )
        content_by_id = self.env["ir.actions.report"]._get_splitted_report(
            pdf_report.report_name, content, report_type
        )

        invoice_data["proforma_pdf_attachment_values"] = {
            "raw": content_by_id[invoice.id],
            "name": invoice._get_invoice_proforma_pdf_report_filename(),
            "mimetype": "application/pdf",
            "res_model": invoice._name,
            "res_id": invoice.id,
        }

    @api.model
    def _hook_invoice_document_after_pdf_report_render(self, invoice, invoice_data):
        return

    @api.model
    def _link_invoice_documents(self, invoices_data):
        attachment_to_create = [
            invoice_data["pdf_attachment_values"]
            for invoice_data in invoices_data.values()
            if invoice_data.get("pdf_attachment_values")
        ]
        _debug.logic(
            "invoice_documents_to_link",
            invoices=len(invoices_data),
            attachments=len(attachment_to_create),
            skipped=not attachment_to_create,
        )
        if not attachment_to_create:
            return

        attachments = self.sudo().env["ir.attachment"].create(attachment_to_create)
        _debug.pipeline("invoice_attachments_created", attachments=attachments)
        res_id_to_attachment = {
            attachment.res_id: attachment for attachment in attachments
        }

        for invoice in invoices_data:
            if attachment := res_id_to_attachment.get(invoice.id):
                invoice.message_main_attachment_id = attachment
                invoice.invalidate_recordset(
                    fnames=["invoice_pdf_report_id", "invoice_pdf_report_file"]
                )
                invoice.is_move_sent = True

    @api.model
    def _hook_if_errors(self, moves_data, allow_raising=True):
        _debug.logic(
            "send_hook_if_errors",
            allow_raising=allow_raising,
            moves_data_count=len(moves_data),
        )
        if allow_raising:
            error_messages = [
                self._format_error_text(move_data["error"])
                for move_data in moves_data.values()
            ]
            if error_messages:
                raise UserError("\n".join(error_messages))
            return

        group_by_partner = defaultdict(list)
        for move, move_data in moves_data.items():
            error = move_data["error"]
            group_by_partner[move_data["author_partner_id"]].append(move.id)
            move.message_post(body=self._format_error_html(error))
        self._send_notifications_to_partners(group_by_partner, is_success=False)

    @api.model
    @_debug.perf.timed
    def _hook_if_success(self, moves_data, from_cron=False):
        group_by_partner = defaultdict(list)
        to_send_mail = {}
        for move, move_data in moves_data.items():
            if from_cron:
                group_by_partner[move_data["author_partner_id"]].append(move.id)
            if "email" in move_data["sending_methods"] and self._is_applicable_to_move(
                "email", move, **move_data
            ):
                to_send_mail[move] = move_data
        _debug.pipeline(
            "send_hook_if_success_mail",
            moves_data_count=len(moves_data),
            to_send_mail_count=len(to_send_mail),
            from_cron=from_cron,
        )
        self._send_mails(to_send_mail, from_cron=from_cron)
        self._send_notifications_to_partners(group_by_partner)

        for move in moves_data:
            if not move.is_invoice(include_receipts=True):
                continue

            try:
                move.journal_id._notify_invoice_subscribers(
                    invoice=move,
                    mail_params={
                        "attachment_ids": [
                            Command.create(
                                {
                                    "name": attachment.name,
                                    "raw": attachment.raw,
                                    "mimetype": attachment.mimetype,
                                }
                            )
                            for attachment in self._get_invoice_extra_attachments(move)
                        ]
                    },
                )
            except Exception:
                _logger.exception("Failed notifying subscribers for move %s", move.id)

    @api.model
    @_debug.perf.timed
    def _send_notifications_to_partners(
        self, moves_grouped_by_author_partner_id, is_success=True
    ):
        _debug.pipeline(
            "send_notifications_dispatching",
            partners=len(moves_grouped_by_author_partner_id or ()),
            is_success=is_success,
        )
        if not moves_grouped_by_author_partner_id:
            return

        def get_account_notification(move_ids, is_success: bool):
            _ = self.env._
            return [
                "account_notification",
                {
                    "type": "success" if is_success else "warning",
                    "title": _("Invoices sent")
                    if is_success
                    else _("Invoices in error"),
                    "message": _("Invoices sent successfully.")
                    if is_success
                    else _("One or more invoices couldn't be processed."),
                    "action_button": {
                        "name": _("Open"),
                        "action_name": _("Sent invoices")
                        if is_success
                        else _("Invoices in error"),
                        "model": "account.move",
                        "res_ids": move_ids,
                    },
                },
            ]

        ResPartner = self.env["res.partner"]
        for partner_id, move_ids in moves_grouped_by_author_partner_id.items():
            partner = ResPartner.browse(partner_id)
            partner._bus_send(*get_account_notification(move_ids, is_success))

    @api.model
    def _send_mail(self, move, mail_template, **kwargs):
        new_message = move.with_context(
            email_notification_allow_footer=True,
            disable_attachment_import=True,
            no_document=True,
        ).message_post(
            message_type="comment",
            **kwargs,
            email_layout_xmlid=self._get_mail_layout(),
            email_add_signature=not mail_template,
            mail_auto_delete=mail_template.auto_delete,
            mail_server_id=mail_template.mail_server_id.id,
            reply_to_force_new=False,
        )

        new_message.attachment_ids.invalidate_recordset(
            ["res_id", "res_model"], flush=False
        )
        if new_message.attachment_ids.ids:
            self.env.cr.execute(
                "UPDATE ir_attachment SET res_id = NULL WHERE id = ANY(%s)",
                [list(new_message.attachment_ids.ids)],
            )
            _debug.perf.count("mail_attachments_detached", rows=self.env.cr.rowcount)
        new_message.attachment_ids.write(
            {
                "res_model": new_message._name,
                "res_id": new_message.id,
            }
        )

    @api.model
    def _get_mail_layout(self):
        return "mail.mail_notification_layout_with_responsible_signature"

    @api.model
    @_debug.perf.timed
    def _prepare_mail_params(self, move, move_data):
        mail_attachments_widget = move_data.get("mail_attachments_widget")
        seen_attachment_ids = set()
        to_exclude = {x["name"] for x in mail_attachments_widget if x.get("skip")}
        for attachment_data in (
            self._prepare_invoice_attachment_entries(move) + mail_attachments_widget
        ):
            if attachment_data["name"] in to_exclude and not attachment_data.get(
                "manual"
            ):
                continue

            try:
                attachment_id = int(attachment_data["id"])
            except ValueError:
                continue

            seen_attachment_ids.add(attachment_id)

        mail_attachments = [
            (attachment.name, attachment.raw)
            for attachment in self.env["ir.attachment"]
            .browse(list(seen_attachment_ids))
            .exists()
        ]

        params = {
            "author_id": move_data["author_partner_id"],
            "body": move_data["mail_body"],
            "subject": move_data["mail_subject"],
            "partner_ids": move_data["mail_partner_ids"],
            "attachments": mail_attachments,
        }
        if move_data.get("reply_to"):
            params["reply_to"] = move_data["reply_to"]
        _debug.pipeline(
            "mail_params_built",
            move=move,
            attachments=len(mail_attachments),
            excluded=len(to_exclude),
            with_reply_to=bool(move_data.get("reply_to")),
        )
        return params

    @api.model
    @_debug.perf.timed
    def _generate_dynamic_reports(self, moves_data, from_cron=False):
        failed = self.env["account.move"]
        for move, move_data in moves_data.items():
            try:
                self._create_dynamic_reports_for_move(move, move_data)
            except Exception:
                _debug.logic("dynamic_report_failed", move=move, from_cron=from_cron)
                if not from_cron:
                    raise
                _logger.exception(
                    "Failed generating dynamic mail reports for move %s", move.id
                )
                move.message_post(
                    body=self.env._(
                        "The document could not be generated, so this invoice was "
                        "not sent by email. Review and resend it manually."
                    )
                )
                failed |= move
        _debug.pipeline(
            "dynamic_reports_generated", moves=len(moves_data), failed=failed
        )
        return failed

    @api.model
    @_debug.perf.timed
    def _create_dynamic_reports_for_move(self, move, move_data):
        mail_attachments_widget = move_data.get("mail_attachments_widget", [])

        dynamic_reports = [
            attachment_widget
            for attachment_widget in mail_attachments_widget
            if attachment_widget.get("dynamic_report")
            and not attachment_widget.get("skip")
        ]

        attachments_to_create = []
        for dynamic_report in dynamic_reports:
            content, _report_format = (
                self.env["ir.actions.report"]
                .with_company(move.company_id)
                .with_context(from_account_move_send=True)
                ._render(dynamic_report["dynamic_report"], move.ids)
            )

            attachments_to_create.append(
                {
                    "raw": content,
                    "name": dynamic_report["name"],
                    "mimetype": "application/pdf",
                    "res_model": move._name,
                    "res_id": move.id,
                }
            )

        attachments = self.env["ir.attachment"].create(attachments_to_create)
        _debug.pipeline(
            "dynamic_reports_rendered",
            move=move,
            reports=len(dynamic_reports),
            attachments=attachments,
        )
        mail_attachments_widget += [
            {
                "id": attachment.id,
                "name": attachment.name,
                "mimetype": "application/pdf",
                "placeholder": False,
                "protect_from_deletion": True,
            }
            for attachment in attachments
        ]

    @api.model
    @_debug.perf.timed
    def _send_mails(self, moves_data, from_cron=False):
        subtype = self.env.ref("mail.mt_comment")

        failed = self._generate_dynamic_reports(moves_data, from_cron=from_cron)

        for move, move_data in [
            (move, move_data)
            for move, move_data in moves_data.items()
            if move not in failed
            and (move.partner_id.email or move_data.get("mail_partner_ids"))
        ]:
            mail_template = move_data["mail_template"]
            mail_lang = move_data["mail_lang"]
            mail_params = self._prepare_mail_params(move, move_data)
            if not mail_params:
                _debug.logic("send_no_mail_params_mail", move=move)
                continue
            _debug.pipeline(
                "send_mailing",
                move=move,
                template=mail_template,
                lang=mail_lang,
                attachments=len(mail_params.get("attachments", [])),
            )

            if move_data.get("proforma_pdf_attachment"):
                attachment = move_data["proforma_pdf_attachment"]
                mail_params["attachments"].append((attachment.name, attachment.raw))

            author_id = mail_params.pop("author_id", False)
            email_from = self._get_mail_default_field_value_from_template(
                mail_template, mail_lang, move, "email_from"
            )
            if email_from or not author_id:
                author_id, email_from = move._message_compute_author(
                    email_from=email_from
                )
            model_description = move.with_context(lang=mail_lang).type_name

            try:
                self._send_mail(
                    move,
                    mail_template,
                    author_id=author_id,
                    subtype_id=subtype.id,
                    model_description=model_description,
                    notify_author_mention=True,
                    email_from=email_from,
                    **mail_params,
                )
            except Exception:
                if not from_cron:
                    raise
                _logger.exception("Failed sending the email for move %s", move.id)
                move.message_post(
                    body=self.env._(
                        "The invoice could not be sent by email. Review and "
                        "resend it manually."
                    )
                )

    @api.model
    def _can_commit(self):
        return not (tools.config["test_enable"] or modules.module.current_test)

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        return

    @api.model
    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        return

    @api.model
    @_debug.perf.timed
    def _render_invoice_documents(self, invoices_data, allow_fallback_pdf=False):
        for invoice, invoice_data in invoices_data.items():
            self._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
            invoice_data["blocking_error"] = invoice_data.get("error") and not (
                allow_fallback_pdf and invoice_data.get("error_but_continue")
            )
            invoice_data["error_but_continue"] = (
                allow_fallback_pdf and invoice_data.get("error_but_continue")
            )

        invoices_data_web_service = {
            invoice: invoice_data
            for invoice, invoice_data in invoices_data.items()
            if not invoice_data.get("error")
        }
        if invoices_data_web_service:
            self._call_web_service_before_invoice_pdf_render(invoices_data_web_service)

        invoices_data_pdf = {
            invoice: invoice_data
            for invoice, invoice_data in invoices_data.items()
            if not invoice_data.get("error") or invoice_data.get("error_but_continue")
        }

        batch_size = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("account.pdf_generation_batch", "80")
        )
        batches = []
        pdf_to_generate = {}
        for invoice, invoice_data in invoices_data_pdf.items():
            if not invoice_data.get("error") and not invoice.invoice_pdf_report_id:
                pdf_to_generate[invoice] = invoice_data

                if len(pdf_to_generate) >= int(batch_size):
                    batches.append(pdf_to_generate)
                    pdf_to_generate = {}

        if pdf_to_generate:
            batches.append(pdf_to_generate)
        _debug.pipeline(
            "send_render_web_service_pdf",
            invoices_data_count=len(invoices_data),
            invoices_data_web_service_count=len(invoices_data_web_service),
            invoices_data_pdf_count=len(invoices_data_pdf),
            batches_count=len(batches),
            batch_size=batch_size,
        )

        for batch in batches:
            with _debug.perf("send_pdf_batch", cr=self.env.cr, batch_count=len(batch)):
                self._update_invoice_data_pdf_report(batch)

        for invoice, invoice_data in invoices_data_pdf.items():
            if not invoice_data.get("error") and not invoice.invoice_pdf_report_id:
                self._hook_invoice_document_after_pdf_report_render(
                    invoice, invoice_data
                )

        if allow_fallback_pdf:
            invoices_data_pdf_error = {
                invoice: invoice_data
                for invoice, invoice_data in invoices_data.items()
                if invoice_data.get("pdf_attachment_values")
                and invoice_data.get("error")
            }
            if invoices_data_pdf_error:
                _debug.logic(
                    "send_pdf_errors_fallback",
                    moves=self.env["account.move"].union(*invoices_data_pdf_error),
                )
                self._hook_if_errors(
                    invoices_data_pdf_error, allow_raising=not allow_fallback_pdf
                )

        invoices_data_web_service = {
            invoice: invoice_data
            for invoice, invoice_data in invoices_data.items()
            if not invoice_data.get("error")
        }
        if invoices_data_web_service:
            self._call_web_service_after_invoice_pdf_render(invoices_data_web_service)

        invoices_to_link = {
            invoice: invoice_data
            for invoice, invoice_data in invoices_data_web_service.items()
            if not invoice_data.get("error") or allow_fallback_pdf
        }
        self._link_invoice_documents(invoices_to_link)

    @api.model
    @_debug.perf.timed
    def _create_invoice_fallback_documents(self, invoices_data):
        for invoice, invoice_data in invoices_data.items():
            if not invoice.invoice_pdf_report_id and invoice_data.get("error"):
                _debug.logic("send_falling_back_proforma_pdf", move=invoice)
                invoice_data.pop("error")
                self._update_invoice_data_proforma_pdf_report(invoice, invoice_data)
                self._hook_invoice_document_after_pdf_report_render(
                    invoice, invoice_data
                )
                invoice_data["proforma_pdf_attachment"] = self.env[
                    "ir.attachment"
                ].create(invoice_data.pop("proforma_pdf_attachment_values"))

    @_debug.perf.timed
    def _check_sending_data(self, moves, **custom_settings):
        self._check_move_constraints(moves)
        self._check_invoice_report(moves, **custom_settings)
        if "sending_methods" in custom_settings and not all(
            sending_method
            in dict(self.env["res.partner"]._fields["invoice_sending_method"].selection)
            for sending_method in custom_settings.get("sending_methods", [])
        ):
            raise ValidationError(_("Invalid sending method provided."))

    @api.model
    @_debug.perf.timed
    def _generate_and_send_invoices(
        self,
        moves,
        from_cron=False,
        allow_raising=True,
        allow_fallback_pdf=False,
        **custom_settings,
    ):
        self._check_sending_data(moves, **custom_settings)
        moves_data = {
            move.sudo(): {
                **self._get_default_sending_settings(
                    move, from_cron=from_cron, **custom_settings
                ),
            }
            for move in moves
        }
        _debug.pipeline(
            "send_generate_and_send_invoices",
            moves=moves,
            from_cron=from_cron,
            fallback=allow_fallback_pdf,
            settings=sorted(custom_settings),
        )

        self._render_invoice_documents(
            moves_data, allow_fallback_pdf=allow_fallback_pdf
        )

        errors = {
            move: move_data
            for move, move_data in moves_data.items()
            if move_data.get("error")
        }
        if errors:
            _debug.logic(
                "send_errors_after_render",
                error_count=len(errors),
                moves=self.env["account.move"].union(*errors),
            )
            self._hook_if_errors(
                errors,
                allow_raising=not from_cron
                and not allow_fallback_pdf
                and allow_raising,
            )

        errors = {
            move: move_data
            for move, move_data in moves_data.items()
            if move_data.get("error")
        }
        if allow_fallback_pdf and errors:
            self._create_invoice_fallback_documents(errors)

        success = {
            move: move_data
            for move, move_data in moves_data.items()
            if not move_data.get("error")
        }
        _debug.pipeline(
            "send_outcome",
            success=len(success),
            error=len(moves_data) - len(success),
            retry=sum(
                1
                for move_data in moves_data.values()
                if move_data.get("error", {}).get("retry")
            ),
        )
        if success:
            self._hook_if_success(success, from_cron=from_cron)

        for move, move_data in moves_data.items():
            if from_cron and move_data.get("error", {}).get("retry"):
                continue
            move.sending_data = False

        attachments = self.env["ir.attachment"]
        for move, move_data in success.items():
            extra_attachments = self._get_invoice_extra_attachments(move)
            attachments += extra_attachments or move_data.get(
                "proforma_pdf_attachment", self.env["ir.attachment"]
            )

        return attachments
