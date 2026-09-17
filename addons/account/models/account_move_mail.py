from markupsafe import Markup

from odoo import _, api, models
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.tools import format_amount, format_date
from odoo.tools.mail import email_re, email_split, generate_tracking_message_id

from odoo.addons.mail.models.mixin_mail_gateway import RouteVerdict

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _mailing_get_default_domain(self, mailing):
        return ["&", ("move_type", "=", "out_invoice"), ("state", "=", "posted")]

    @api.model
    @_debug.perf.timed
    def _routing_check_route(self, message, message_dict, route, raise_exception=True):
        if route[0] == "account.move" and len(message_dict["attachments"]) < 1:
            company_id = (route[2] or {}).get("company_id", self.env.company.id)
            if not isinstance(company_id, int):
                raise ValueError(
                    f"Default value for 'company_id' for {route[4]} is not an integer"
                )
            journal_alias_company = self.env["res.company"].search(
                [["id", "=", company_id]]
            )
            body = self.env["ir.qweb"]._render(
                "account.email_template_mail_gateway_failed",
                {
                    "company_email": journal_alias_company.email
                    or self.env.company.email,
                    "company_name": journal_alias_company.name or self.env.company.name,
                },
            )
            reply_to_journal_company = (
                journal_alias_company.email or self.env.company.email
            )
            self.with_company(journal_alias_company)._routing_create_bounce_email(
                message_dict["from"],
                body,
                message,
                references=f"{message_dict['message_id']} {generate_tracking_message_id('loop-detection-bounce-email')}",
                reply_to=reply_to_journal_company,
            )
            _debug.logic(
                "mail_route_refused",
                company=company_id,
                reason="no_attachments",
            )
            return RouteVerdict.REFUSED
        return super()._routing_check_route(
            message, message_dict, route, raise_exception=raise_exception
        )

    @api.model
    @_debug.perf.timed
    def message_new(self, msg_dict, custom_values=None):
        custom_values = custom_values or {}
        if custom_values.get("move_type", "entry") not in (
            "out_invoice",
            "in_invoice",
            "entry",
        ):
            return super().message_new(msg_dict, custom_values=custom_values)

        self = self.with_context(skip_is_manually_modified=True)

        company = (
            self.env["res.company"].browse(custom_values["company_id"])
            if custom_values.get("company_id")
            else self.env.company
        )

        def is_internal_partner(partner):
            return company.partner_id in (partner | partner.parent_id) or (
                partner.user_ids
                and all(user._is_internal() for user in partner.user_ids)
            )

        def filter_found(partner):
            return (
                not company
                or partner.company_id.id in [False, company.id]
                or partner.partner_share
            )

        from_mail_addresses = email_split(msg_dict.get("from", ""))
        partners = self._partner_get_or_create_from_emails_single(
            from_mail_addresses, filter_found=filter_found, no_create=True
        )
        if (
            partners
            and is_internal_partner(partners[0])
            and (
                body_mail_addresses := set(email_re.findall(msg_dict.get("body") or ""))
            )
        ):
            partners = self._partner_get_or_create_from_emails_single(
                body_mail_addresses, filter_found=filter_found, no_create=True
            )

        partners = partners.filtered(lambda p: not is_internal_partner(p))

        if msg_dict.get("subject") and msg_dict.get("body"):
            msg_dict["body"] = Markup("<div><div><h3>%s</h3></div>%s</div>") % (
                msg_dict["subject"],
                msg_dict["body"],
            )

        values = {
            "name": "/",
            "invoice_source_email": (
                from_mail_addresses[0] if from_mail_addresses else False
            ),
            "partner_id": partners[0].id if partners else False,
        }
        move_ctx = self.with_context(
            from_alias=True,
            default_move_type=custom_values.get("move_type", "entry"),
            default_journal_id=custom_values.get("journal_id"),
            default_company_id=company.id,
        )
        move = super(AccountMove, move_ctx).message_new(msg_dict, custom_values=values)
        self.env.add_to_compute(move._fields["name"], move)
        _debug.pipeline(
            "alias_created_mail",
            move=move,
            type=custom_values.get("move_type", "entry"),
            journal=custom_values.get("journal_id"),
            company=company,
            partner=values["partner_id"],
            from_=values["invoice_source_email"],
        )

        return move

    def _attachment_fields_to_clear(self):
        return super()._attachment_fields_to_clear() + ["message_main_attachment_id"]

    @_debug.perf.timed
    def _message_post_after_hook_from_alias(
        self, new_message, message_values, valid_files_data, extra_files_data
    ):
        file_data_groups = self._group_files_data_into_groups_of_mixed_types(
            valid_files_data
        ) or [[]]
        invoices = self
        _debug.pipeline(
            "alias_file",
            move=self,
            valid_files_data_count=len(valid_files_data),
            extra_files_data_count=len(extra_files_data),
            file_data_groups_count=len(file_data_groups),
        )
        if len(file_data_groups) > 1:
            create_vals = [
                self.copy_data()[0].copy()
                for _unused in range(len(file_data_groups) - 1)
            ]
            invoices |= self.with_context(skip_is_manually_modified=True).create(
                create_vals
            )

        for invoice, file_data_group in zip(invoices, file_data_groups, strict=False):
            attachment_records = self._from_files_data(file_data_group)
            if invoice == self:
                attachment_records |= self._from_files_data(extra_files_data)
                new_message.attachment_ids = [Command.set(attachment_records.ids)]
                message_values["attachment_ids"] = [
                    Command.link(attachment.id) for attachment in attachment_records
                ]
                res = super(
                    AccountMove, self.with_context(no_document=True)
                )._message_post_after_hook(new_message, message_values)
            else:
                sub_new_message = new_message.copy(
                    {
                        "res_id": invoice.id,
                        "attachment_ids": [Command.set(attachment_records.ids)],
                    }
                )
                sub_message_values = {
                    **message_values,
                    "res_id": invoice.id,
                    "attachment_ids": [
                        Command.link(attachment.id) for attachment in attachment_records
                    ],
                }
                super(
                    AccountMove, invoice.with_context(no_document=True)
                )._message_post_after_hook(sub_new_message, sub_message_values)
            invoice._fix_attachments_on_record_from_files_data(
                file_data_group, extra_files_data
            )

        for invoice, file_data_group in zip(invoices, file_data_groups, strict=False):
            if file_data_group:
                invoice._extend_with_attachments(file_data_group, new=True)

        invoices._message_post_from_alias_done()

        return res

    def _message_post_from_alias_done(self):
        return

    @_debug.perf.timed
    def _message_post_after_hook(self, new_message, message_values):
        attachments = new_message.attachment_ids

        if _debug.logic.enabled:
            _debug.logic(
                "attachment_import_gate",
                move=self,
                attachments=len(attachments),
                message_type=new_message.message_type,
                disabled=bool(self.env.context.get("disable_attachment_import")),
            )
        if (
            not attachments
            or new_message.message_type not in {"email", "comment"}
            or self.env.context.get("disable_attachment_import")
        ):
            return super()._message_post_after_hook(new_message, message_values)

        files_data = self._to_files_data(attachments)

        files_data.extend(self._unwrap_attachments(files_data))

        valid_files_data = []
        extra_files_data = []
        for file_data in files_data:
            if (
                self._is_record_attachment_required(file_data["attachment"])
                or file_data["xml_tree"] is not None
            ):
                valid_files_data.append(file_data)
            else:
                extra_files_data.append(file_data)

        _debug.pipeline(
            "attachments_classified",
            move=self,
            files=len(files_data),
            valid=len(valid_files_data),
            extra=len(extra_files_data),
            from_alias=bool(self.env.context.get("from_alias")),
        )
        if self.env.context.get("from_alias"):
            return self._message_post_after_hook_from_alias(
                new_message, message_values, valid_files_data, extra_files_data
            )

        attachment_records = self._from_files_data(files_data)
        self._fix_attachments_on_record_from_files_data(
            valid_files_data, extra_files_data
        )

        if self.env.user.active and self.env.user._is_internal():
            self._extend_with_attachments(files_data)

        _debug.pipeline(
            "attachments_relinked",
            move=self,
            attachments=attachment_records,
        )
        new_message.attachment_ids = [Command.set(attachment_records.ids)]
        message_values["attachment_ids"] = [
            Command.link(attachment.id) for attachment in attachment_records
        ]
        return super()._message_post_after_hook(new_message, message_values)

    def _creation_subtype(self):
        if self.move_type in ("out_invoice", "out_receipt"):
            return self.env.ref("account.mt_invoice_created")
        else:
            return super()._creation_subtype()

    def _track_subtype(self, init_values):
        self.check_singleton()

        if not self.is_invoice(include_receipts=True):
            _debug.logic(
                "track_subtype_non_invoice",
                move=self,
                state_changed="state" in init_values,
            )
            if self.origin_payment_id and "state" in init_values:
                self.origin_payment_id._message_track(
                    ["state"], {self.origin_payment_id.id: init_values}
                )
            return super()._track_subtype(init_values)

        if "payment_state" in init_values and self.payment_state == "paid":
            _debug.logic("track_subtype_paid", move=self)
            return self.env.ref("account.mt_invoice_paid")
        elif (
            "state" in init_values
            and self.state == "posted"
            and self.is_sale_document(include_receipts=True)
        ):
            _debug.logic("track_subtype_validated", move=self)
            return self.env.ref("account.mt_invoice_validated")
        return super()._track_subtype(init_values)

    def _creation_message(self):
        if not self.is_invoice(include_receipts=True):
            return super()._creation_message()
        return {
            "out_invoice": _("Invoice Created"),
            "out_refund": _("Credit Note Created"),
            "in_invoice": _("Vendor Bill Created"),
            "in_refund": _("Refund Created"),
            "out_receipt": _("Sales Receipt Created"),
            "in_receipt": _("Purchase Receipt Created"),
        }[self.move_type]

    @_debug.perf.timed
    def _notify_by_email_prepare_rendering_context(
        self,
        message,
        msg_vals=False,
        model_description=False,
        force_email_company=False,
        force_email_lang=False,
        force_record_name=False,
        tracking_values=None,
    ):
        render_context = super()._notify_by_email_prepare_rendering_context(
            message,
            msg_vals=msg_vals,
            model_description=model_description,
            force_email_company=force_email_company,
            force_email_lang=force_email_lang,
            force_record_name=force_record_name,
            tracking_values=tracking_values,
        )
        record = render_context["record"]
        subtitles = [
            f"{record.display_name} - {record.partner_id.name}"
            if record.partner_id.name
            else record.display_name
        ]
        if self.is_invoice(include_receipts=True):
            if _debug.logic.enabled:
                _debug.logic(
                    "email_subtitle_due_shown",
                    move=self,
                    due=bool(self.invoice_date_due)
                    and self.payment_state not in ("in_payment", "paid"),
                )
            if self.invoice_date_due and self.payment_state not in (
                "in_payment",
                "paid",
            ):
                subtitles.append(
                    _(
                        "%(amount)s due\N{NO-BREAK SPACE}%(date)s",
                        amount=format_amount(
                            self.env,
                            self.amount_total
                            or self.tax_totals.get("total_amount_currency", 0),
                            self.currency_id,
                            lang_code=render_context.get("lang"),
                        ),
                        date=format_date(
                            self.env,
                            self.invoice_date_due,
                            lang_code=render_context.get("lang"),
                        ),
                    )
                )
            else:
                subtitles.append(
                    format_amount(
                        self.env,
                        self.amount_total
                        or self.tax_totals.get("total_amount_currency", 0),
                        self.currency_id,
                        lang_code=render_context.get("lang"),
                    )
                )
        render_context["subtitles"] = subtitles
        return render_context

    def _get_mail_thread_data_attachments(self):
        res = super()._get_mail_thread_data_attachments()
        Send = self.env["mixin.account.move.send"]
        for move in self:
            res[move.id] |= Send._get_invoice_extra_attachments(move)
        return res
