from odoo import api, models

# Labels used by an app for its "Configuration" menu. Thai labels are included
# because a few menus are named in Thai directly in the source XML.
CONFIGURATION_MENU_LABELS = ("Configuration", "ตั้งค่า", "การตั้งค่า")

# Order of the apps in the app switcher, grouped into business-flow *clusters*
# so that the apps used together sit next to each other: front office, finance,
# marketing, procurement, projects, people, website/content and finally the
# internal tools. Each entry is ``(cluster_label, (menu_xmlid, ...))``.
#
# The label is documentation only -- the Odoo 19 switcher is a flat grid with
# no folders or group headers -- so the clustering is expressed purely through
# the ``sequence`` handed out below: every cluster owns its own block of
# sequence numbers (see APP_MENU_CLUSTER_GAP) and the apps inside a cluster are
# ordered by their position in the tuple. Apps of modules that are not
# installed are skipped, so the list may safely reference optional modules.
# Only *top-level* menus may be listed: the sequence is applied whatever the
# menu's parent, so a section of another application would be pushed to the
# end of that application instead of being ordered inside it.
APP_MENU_CLUSTERS = (
    ("Front office", (
        "mail.menu_root_discuss",
        "calendar.mail_menu_calendar",
        "contacts.menu_contacts",
        "crm.crm_menu_root",
        "sale.sale_menu_root",
        "point_of_sale.menu_point_root",
    )),
    ("Finance and analytics", (
        "account.menu_finance",
        "spreadsheet_dashboard.spreadsheet_dashboard_menu_root",
    )),
    ("Marketing and engagement", (
        "mass_mailing.mass_mailing_menu_root",
        "mass_mailing_sms.mass_mailing_sms_menu_root",
        "event.event_main_menu",
        "survey.menu_surveys",
        "im_livechat.menu_livechat_root",
        "marketing_card.card_menu",
        "utm.menu_link_tracker_root",
    )),
    ("Procurement and supply chain", (
        "purchase.menu_purchase_root",
        "purchase_request.parent_menu_purchase_request",
        "stock_request.menu_stock_request_root",
        "stock.menu_stock_root",
        "mrp.menu_mrp_root",
        "repair.menu_repair_order",
        "maintenance.menu_maintenance_title",
    )),
    ("Projects and services", (
        "project.menu_main_pm",
        "hr_timesheet.timesheet_menu_root",
        "helpdesk_mgmt.helpdesk_ticket_main_menu",
        "od19_document_sign.menu_od19_document_sign_root",
    )),
    ("Human resources", (
        "hr.menu_hr_root",
        "hr_attendance.menu_hr_attendance_root",
        "hr_recruitment.menu_hr_recruitment_root",
        "fleet.menu_root",
        "hr_holidays.menu_hr_holidays_root",
        "hr_expense.menu_hr_expense_root",
        "lunch.menu_lunch",
    )),
    ("Website and content", (
        "website.menu_website_configuration",
        "website_slides.website_slides_menu_root",
        "document_knowledge.menu_document_root",
        "od19_announcement.announcement_main_menu",
        "od19_iso_document_control.menu_iso_root",
    )),
    ("Internal tools", (
        "project_todo.menu_todo_todos",
        "data_recycle.menu_data_cleaning_root",
        "od19_user_guide_tours.menu_od19_user_guide_root",
    )),
)

# Sequence layout. The first app of the first cluster gets
# APP_MENU_SEQUENCE_START; each following app inside a cluster is
# APP_MENU_SEQUENCE_STEP further on. Every new cluster jumps forward by
# APP_MENU_CLUSTER_GAP, which leaves free numbers between two clusters so a new
# app can be inserted into a cluster without renumbering the whole list and so
# the boundary between clusters stays obvious in the raw data.
APP_MENU_SEQUENCE_START = 10
APP_MENU_SEQUENCE_STEP = 10
APP_MENU_CLUSTER_GAP = 100

# The "Apps" and "Settings" tiles must stay at the very end of the switcher.
# The curated block built from the clusters above extends past their original
# sequences (500/550), so they are pushed after the last curated app; otherwise
# they would land in the middle of the clusters.
APP_MENU_ADMINISTRATION_XMLIDS = (
    "base.menu_management",
    "base.menu_administration",
)

# Context key set while re-sequencing to keep the ``create``/``write`` overrides
# below from re-entering the same logic.
APP_MENU_REORDER_CONTEXT = "od19_app_menu_reorder"


def od19_app_menu_sequences():
    """Yield ``(xmlid, sequence)`` for every curated app, in display order."""
    for cluster_index, (_label, xmlids) in enumerate(APP_MENU_CLUSTERS):
        base = APP_MENU_SEQUENCE_START + cluster_index * APP_MENU_CLUSTER_GAP
        for index, xmlid in enumerate(xmlids):
            yield xmlid, base + index * APP_MENU_SEQUENCE_STEP


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model_create_multi
    def create(self, vals_list):
        menus = super().create(vals_list)
        menus._od19_reorder_app_menus_if_root()
        return menus

    def write(self, vals):
        res = super().write(vals)
        if "sequence" in vals or "parent_id" in vals:
            self._od19_reorder_app_menus_if_root()
        return res

    def _od19_reorder_app_menus_if_root(self):
        """Re-apply the app ordering whenever a top-level menu is created/moved.

        Odoo rewrites the ``sequence`` of every menu owned by a module each time
        that module is installed or upgraded, which would shuffle the apps back
        into their default order on the next ``-u``. Re-applying the curated
        order on the fly keeps it in place without touching the core data files.
        """
        if self.env.context.get(APP_MENU_REORDER_CONTEXT):
            return
        if not any(not menu.parent_id for menu in self):
            return
        self.env["ir.ui.menu"].with_context(
            **{APP_MENU_REORDER_CONTEXT: True}
        )._od19_sequence_app_menus()

    @api.model
    def _od19_sequence_app_menus(self):
        """Order the top-level app menus by business-flow cluster.

        The app/sequence pairs come from :func:`od19_app_menu_sequences` (see
        ``APP_MENU_CLUSTERS``). The writes are done under the reorder context so
        the ``create``/``write`` overrides above do not re-enter this method
        while it is running, which keeps the method idempotent and free of
        redundant nested reorders.
        """
        menu_model = self.env["ir.ui.menu"].with_context(
            **{APP_MENU_REORDER_CONTEXT: True}
        )
        sequences = list(od19_app_menu_sequences())
        for xmlid, sequence in sequences:
            menu = menu_model.env.ref(xmlid, raise_if_not_found=False)
            if not menu:
                continue
            if menu.sequence != sequence:
                menu.sequence = sequence
        # Keep the Apps/Settings tiles after every curated app. The last
        # sequence is taken from the full list (not only the installed apps) so
        # the values stay stable whatever subset of modules is installed.
        last_sequence = sequences[-1][1]
        for offset, xmlid in enumerate(APP_MENU_ADMINISTRATION_XMLIDS, start=1):
            menu = menu_model.env.ref(xmlid, raise_if_not_found=False)
            if not menu:
                continue
            sequence = last_sequence + offset * APP_MENU_SEQUENCE_STEP
            if menu.sequence != sequence:
                menu.sequence = sequence

    @api.model
    def _od19_place_configuration_menus_last(self):
        """Move every Configuration menu to the end of its parent menu.

        Odoo reloads menu data on each module update and resets the ``sequence``
        of the menus it owns, so the rule is re-applied from
        ``data/ui_defaults.xml`` on every install/upgrade.
        """
        # Search in the source language so the lookup is independent from the
        # language the data is loaded with.
        menus = self.with_context(lang="en_US").search([
            ("name", "in", CONFIGURATION_MENU_LABELS),
            ("parent_id", "!=", False),
        ])
        for menu in menus:
            siblings = self.search([
                ("parent_id", "=", menu.parent_id.id),
                ("id", "!=", menu.id),
            ])
            if not siblings:
                continue
            last_sequence = max(siblings.mapped("sequence"))
            if menu.sequence <= last_sequence:
                menu.sequence = last_sequence + 1
