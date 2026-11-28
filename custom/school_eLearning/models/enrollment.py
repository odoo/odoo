# -*- coding: utf-8 -*-
from odoo import api, models


class UniversityEnrollment(models.Model):
    _inherit = "university.enrollment"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        enrolled_records = records.filtered(lambda r: r.status == "enrolled")
        if enrolled_records:
            enrolled_records._elearning_add_members()
        return records

    def write(self, vals):
        old_sections = {}
        if "class_section_id" in vals:
            for rec in self.filtered(lambda r: r.status == "enrolled"):
                old_sections[rec.id] = rec.class_section_id

        res = super().write(vals)

        if old_sections:
            for rec in self.filtered(lambda r: r.status == "enrolled"):
                old_sec = old_sections.get(rec.id)
                if old_sec and old_sec != rec.class_section_id:
                    rec._elearning_remove_members_for_section(old_sec)
                    rec._elearning_add_members()

        if "status" in vals:
            if vals["status"] == "enrolled":
                self.filtered(lambda r: r.status == "enrolled")._elearning_add_members()
            elif vals["status"] in ("dropped", "withdrawn"):
                self.filtered(lambda r: r.status in ("dropped", "withdrawn"))._elearning_remove_members()
        return res

    def unlink(self):
        enrolled = self.filtered(lambda r: r.status == "enrolled")
        if enrolled:
            enrolled._elearning_remove_members()
        return super().unlink()

    def action_confirm(self):
        result = super().action_confirm()
        self._elearning_add_members()
        return result

    def action_drop(self):
        result = super().action_drop()
        self._elearning_remove_members()
        return result

    def action_withdraw(self):
        result = super().action_withdraw()
        self._elearning_remove_members()
        return result

    def _elearning_partner(self):
        self.ensure_one()
        user = self.student_id.user_id
        return user.partner_id if user else self.env["res.partner"]

    def _elearning_add_members(self):
        for enrollment in self:
            if enrollment.status != "enrolled":
                continue
            partner = enrollment._elearning_partner()
            channels = enrollment.class_section_id.slide_channel_ids
            if not partner or not channels:
                continue
            channels.sudo()._action_add_members(partner)

    def _elearning_remove_members(self):
        for enrollment in self:
            partner = enrollment._elearning_partner()
            channels = enrollment.class_section_id.slide_channel_ids
            if not partner or not channels:
                continue
            # Keep membership if student is actively enrolled in another section sharing these channels
            other_active = self.env["university.enrollment"].search([
                ("id", "!=", enrollment.id),
                ("student_id", "=", enrollment.student_id.id),
                ("status", "=", "enrolled"),
                ("class_section_id.slide_channel_ids", "in", channels.ids),
            ])
            other_channels = other_active.mapped("class_section_id.slide_channel_ids")
            channels_to_remove = channels - other_channels
            if channels_to_remove:
                existing = self.env["slide.channel.partner"].sudo().search([
                    ("channel_id", "in", channels_to_remove.ids),
                    ("partner_id", "=", partner.id),
                ])
                if existing:
                    existing.mapped("channel_id").sudo()._remove_membership(partner.ids)

    def _elearning_remove_members_for_section(self, section):
        """Remove membership when section changes, unless student is enrolled in another section sharing channels."""
        if not section:
            return
        for enrollment in self:
            partner = enrollment._elearning_partner()
            channels = section.slide_channel_ids
            if not partner or not channels:
                continue
            other_active = self.env["university.enrollment"].search([
                ("id", "!=", enrollment.id),
                ("student_id", "=", enrollment.student_id.id),
                ("status", "=", "enrolled"),
                ("class_section_id.slide_channel_ids", "in", channels.ids),
            ])
            other_channels = other_active.mapped("class_section_id.slide_channel_ids")
            channels_to_remove = channels - other_channels
            if channels_to_remove:
                existing = self.env["slide.channel.partner"].sudo().search([
                    ("channel_id", "in", channels_to_remove.ids),
                    ("partner_id", "=", partner.id),
                ])
                if existing:
                    existing.mapped("channel_id").sudo()._remove_membership(partner.ids)
