# -*- coding: utf-8 -*-
from odoo import api, models

# ---------------------------------------------------------------------------
# App-scoped user-guide tours
# ---------------------------------------------------------------------------
# xml_id of the application root menu  ->  tour started the first time the
# user opens that application.
#
# The OD19 guide tours are stored with ``custom = True``. That flag keeps them
# out of the core *sequential* onboarding queue (``web_tour.tour``
# ``get_current_tour()`` only returns ``custom = False`` tours, consumed one
# after the other in ``sequence`` order). Instead the tours are started on
# demand by ``od19_guide_tour_service`` (static/src/js) as soon as the user
# opens the matching application, so the user no longer has to open one
# particular app first.
OD19_GUIDE_APP_TOURS = [
    ("contacts.menu_contacts", "od19_contacts_credit_risk_tour"),
    ("sale.sale_menu_root", "od19_sales_contract_billing_tour"),
    ("purchase.menu_purchase_root", "od19_purchase_approval_tour"),
    ("stock.menu_stock_root", "od19_inventory_operations_tour"),
    ("account.menu_finance", "od19_accounting_tour"),
    ("hr_expense.menu_hr_expense_root", "od19_hr_expense_tour"),
    ("project.menu_main_pm", "od19_project_analytic_tour"),
    ("fleet.menu_root", "od19_fleet_accounting_tour"),
    ("maintenance.menu_maintenance_title", "od19_asset_loan_tour"),
    ("repair.menu_repair_order", "od19_warranty_tour"),
    ("hr_attendance.menu_hr_attendance_root", "od19_hr_attendance_zkteco_tour"),
    ("calendar.mail_menu_calendar", "od19_meeting_room_booking_tour"),
    ("document_knowledge.menu_document_root", "od19_knowledge_tour"),
    ("od19_announcement.announcement_main_menu", "od19_announcement_tour"),
    ("od19_iso_document_control.menu_iso_root", "od19_iso_document_control_tour"),
    # Applications installed / updated later. Each entry must point at a
    # *top-level* application menu: one app root maps to exactly one tour.
    # Guides that live inside another application (e-Tax Invoice under
    # Accounting, Audit Counts under Inventory, Sale Order Print under Sales)
    # keep their own app root and stay reachable from the User Guide menu or
    # from /odoo?tour=<tour_name>.
    ("od19_document_sign.menu_od19_document_sign_root", "od19_signing_tour"),
    ("od19_helpdesk_extension.menu_internal_helpdesk", "od19_internal_helpdesk_tour"),
    ("stock_request.menu_stock_request_root", "od19_goods_issue_tour"),
    ("website.menu_website_configuration", "od19_recruitment_tour"),
    ("spreadsheet_dashboard.spreadsheet_dashboard_menu_root", "od19_dashboard_tour"),
    ("base.menu_administration", "od19_misc_features_tour"),
]


class WebTourTour(models.Model):
    _inherit = "web_tour.tour"

    @api.model
    def get_current_tour(self):
        """Silence the core sequential onboarding queue while guide tours remain.

        Core ``get_current_tour`` returns the first unconsumed ``custom = False``
        tour, whatever application the user is browsing. On this deployment the
        OD19 guide tours are the onboarding experience: ``od19_guide_tour_service``
        starts the tour of the application the user opens. The core queue would
        otherwise hijack the very first application opened (usually the CRM or
        Sales tour phone the user never asked for) and the guide tours would
        never show up. As long as the current user still has a guide tour to
        discover, the core queue stays silent.
        """
        if self.env.user and self.env.user.tour_enabled and self.env.user._is_internal():
            guide_names = [tour_name for _xmlid, tour_name in OD19_GUIDE_APP_TOURS]
            pending = self.search_count([
                ("name", "in", guide_names),
                ("user_consumed_ids", "not in", self.env.user.id),
            ])
            if pending:
                return False
        return super().get_current_tour()

    @api.model
    def od19_guide_get_app_tours(self):
        """Return the app menu id -> tour mapping for the current user.

        Only ``id`` / ``name`` of the menu and the consumption state are
        exposed so that the guide service can start the right tour when the
        user opens an application for the first time.

        The consumption state is the core one: a guide tour is marked as seen
        by ``web_tour.tour.consume``, which the web client calls when the user
        reaches the last step of the tour. A tour that is left unfinished is
        therefore still reported as ``consumed = False`` and is proposed again
        the next time the application is opened.
        """
        IrModelData = self.env["ir.model.data"].sudo()
        result = []
        for xmlid, tour_name in OD19_GUIDE_APP_TOURS:
            menu_id = IrModelData._xmlid_to_res_id(xmlid, raise_if_not_found=False)
            if not menu_id:
                continue
            tour = self.sudo().search([("name", "=", tour_name)], limit=1)
            if not tour:
                continue
            result.append({
                "menuId": menu_id,
                "tourName": tour.name,
                "consumed": self.env.user.id in tour.user_consumed_ids.ids,
            })
        return result
