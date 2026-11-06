# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

# แผนที่บทบาท ↔ กลุ่ม (ตรงตาม Role Matrix §7 ของสเปก)
# key = xml id ของ res.users.role, value = เซตของ xml id ของกลุ่มที่ต้อง imply
ROLE_MATRIX = {
    # A. Governance / IT
    "role_system_manager": {
        "base.group_system",
        "base.group_erp_manager",
        "od19_security_roles.group_od19_department_all",
    },
    "role_access_administrator": {
        "od19_security_roles.group_od19_role_manager",
        "base.group_user",
    },
    "role_integration_manager": {
        "od19_currency_rate_bot.group_currency_rate_bar_viewer",
    },
    # B. Sales
    "role_sales_user": {"sales_team.group_sale_salesman"},
    "role_sales_manager": {"sales_team.group_sale_manager"},
    "role_sales_director": {
        "od19_sales_oca_bridge_workflow.group_sale_director",
        "sales_team.group_sale_manager",
    },
    "role_credit_reviewer": {
        "od19_sales_customer_risk_gate.group_od19_credit_reviewer",
        "od19_security_roles.group_od19_credit_approver",
    },
    "role_sales_project_officer": {
        "project.group_project_user",
        "sales_team.group_sale_salesman",
    },
    # C. Purchase
    "role_purchase_user": {"purchase.group_purchase_user"},
    "role_purchase_manager": {"purchase.group_purchase_manager"},
    "role_purchase_director": {
        "od19_purchase_procurement_core.group_purchase_director",
    },
    # D. Inventory & Logistics
    "role_warehouse_user": {"stock.group_stock_user"},
    "role_warehouse_manager": {
        "stock.group_stock_manager",
        "od19_security_roles.group_od19_department_all",
    },
    "role_goods_issue_operator": {"stock_request.group_stock_request_user"},
    "role_transportation_officer": {"stock.group_stock_user"},
    "role_inventory_counter": {"stock.group_stock_user"},
    # E. Accounting & Finance
    "role_accountant": {
        "account.group_account_user",
        "od19_security_roles.group_od19_department_all",
    },
    "role_finance_manager": {
        "account.group_account_manager",
        "od19_security_roles.group_od19_department_all",
        "od19_security_roles.group_od19_credit_approver",
    },
    "role_cashier": {
        "account.group_account_invoice",
        "account.group_account_user",
    },
    "role_cheque_officer": {
        "account.group_account_invoice",
        "account.group_account_user",
    },
    "role_wht_officer": {"base.group_user", "account.group_account_user"},
    # F. After-Sales / Service
    "role_service_advisor": {"od19_helpdesk_extension.group_sales_service"},
    "role_qc_inspector": {"base.group_user"},
    "role_document_signer": {
        "od19_document_sign.group_od19_document_sign_user",
    },
    "role_document_signer_manager": {
        "od19_document_sign.group_od19_document_sign_manager",
    },
    "role_service_manager": {"base.group_user", "account.group_account_manager"},
    # G. Human Resources
    "role_hr_user": {"hr.group_hr_user"},
    "role_hr_manager": {
        "hr.group_hr_manager",
        "od19_security_roles.group_od19_department_all",
    },
    "role_fleet_manager": {"fleet.fleet_group_manager"},
    "role_meeting_room_manager": {
        "od19_meeting_room_booking.group_meeting_room_manager",
    },
    "role_expense_ceo_approver": {
        "od19_hr_expense_thai.group_od19_expense_ceo_approver",
    },
    # H. ISO / Quality / Risk
    "role_document_controller": {"base.group_user", "base.group_system"},
    "role_internal_auditor": {"base.group_user", "base.group_system"},
    "role_risk_owner": {"base.group_user", "base.group_system"},
    "role_management_review_member": {"base.group_user", "base.group_system"},
    "role_supplier_quality_officer": {"base.group_user", "base.group_system"},
    # I. Reporting & Dashboard
    "role_dashboard_user": {"od19_dashboard.group_od19_dashboard_user"},
    "role_dashboard_manager": {"od19_dashboard.group_od19_dashboard_manager"},
    "role_reporting_viewer": {"account.group_account_invoice"},
    "role_reporting_analyst": {
        "od19_security_roles.group_od19_department_all",
        "account.group_account_invoice",
    },
    # J. Support & Collaboration
    "role_employee_base": {
        "base.group_user",
        "od19_security_roles.group_od19_department_scope",
    },
    "role_meeting_room_user": {
        "od19_meeting_room_booking.group_meeting_room_user",
    },
    "role_helpdesk_internal": {
        "od19_helpdesk_extension.group_internal_helpdesk",
    },
    "role_knowledge_user": {
        "base.group_user",
        "document_knowledge.group_document_user",
    },
}

SALES_GROUPS = {
    "sales_team.group_sale_salesman",
    "sales_team.group_sale_manager",
}
CREDIT_APPROVER_GROUP = "od19_security_roles.group_od19_credit_approver"


@tagged("post_install", "-at_install")
class TestRoleCatalog(TransactionCase):
    """ตรวจว่า Role Catalog โหลดครบและผูกกลุ่มตรงตาม Role Matrix §7"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.role_model = cls.env["res.users.role"]
        cls.privilege = cls.env.ref("od19_security_roles.od19_role_privilege")

    def _role(self, xml_id):
        return self.env.ref("od19_role_catalog.%s" % xml_id)

    def test_all_roles_are_loaded(self):
        """บทบาททุกตัวใน matrix ต้องโหลดได้ (44 บทบาท)"""
        missing = []
        for xml_id in ROLE_MATRIX:
            if not self.env.ref(
                "od19_role_catalog.%s" % xml_id, raise_if_not_found=False
            ):
                missing.append(xml_id)
        self.assertFalse(missing, "บทบาทที่โหลดไม่สำเร็จ: %s" % ", ".join(missing))
        self.assertEqual(len(ROLE_MATRIX), 44, "Role Matrix ต้องมี 44 บทบาท")

    def test_roles_belong_to_od19_privilege(self):
        """บทบาททุกตัวต้องอยู่ใต้ privilege OD19 Roles"""
        for xml_id in ROLE_MATRIX:
            role = self._role(xml_id)
            self.assertEqual(
                role.group_privilege_id,
                self.privilege,
                "บทบาท %s ไม่ได้อยู่ใต้ privilege OD19 Roles" % xml_id,
            )

    def test_implied_groups_match_matrix(self):
        """implied_ids ของแต่ละบทบาทต้องมีกลุ่มครบตาม matrix"""
        for xml_id, expected_groups in ROLE_MATRIX.items():
            role = self._role(xml_id)
            expected_ids = {self.env.ref(ref).id for ref in expected_groups}
            missing = expected_ids - set(role.implied_ids.ids)
            self.assertFalse(
                missing,
                "บทบาท %s ขาดกลุ่ม: %s"
                % (
                    xml_id,
                    ", ".join(
                        self.env["res.groups"].browse(missing).mapped("display_name")
                    ),
                ),
            )

    def test_role_names_are_unique_per_privilege(self):
        """ชื่อบทบาทต้องไม่ซ้ำกัน (ตรงกับ unique constraint ของ res.groups)"""
        roles = self.role_model.search(
            [("group_privilege_id", "=", self.privilege.id)]
        )
        names = roles.mapped("name")
        self.assertEqual(
            len(names), len(set(names)), "พบบทบาทที่ชื่อซ้ำกัน: %s" % names
        )

    def test_no_sales_credit_overlap(self):
        """SoD: ต้องไม่มีบทบาทใดให้ทั้งสิทธิ์ฝั่งขายและสิทธิ์อนุมัติเครดิต"""
        sales_ids = {self.env.ref(ref).id for ref in SALES_GROUPS}
        credit_id = self.env.ref(CREDIT_APPROVER_GROUP).id
        offenders = self.role_model.search([]).filtered(
            lambda role: credit_id in role.implied_ids.ids
            and sales_ids & set(role.implied_ids.ids)
        )
        self.assertFalse(
            offenders,
            "พบบทบาทที่ละเมิด SoD (ขาย + อนุมัติเครดิต): %s"
            % ", ".join(offenders.mapped("name")),
        )

    def test_only_finance_roles_can_approve_credit(self):
        """มีเพียง role_credit_reviewer และ role_finance_manager ที่อนุมัติเครดิตได้"""
        credit_id = self.env.ref(CREDIT_APPROVER_GROUP).id
        holders = {
            xml_id
            for xml_id in ROLE_MATRIX
            if credit_id in self._role(xml_id).implied_ids.ids
        }
        self.assertEqual(
            holders, {"role_credit_reviewer", "role_finance_manager"}
        )

    def test_employee_base_is_default_role(self):
        """role_employee_base ต้องเป็นบทบาทพื้นฐานที่ให้ผู้ใช้ใหม่โดยอัตโนมัติ"""
        role = self._role("role_employee_base")
        self.assertTrue(role.is_default)
        defaults = self.role_model.search([("is_default", "=", True)])
        self.assertEqual(defaults, role)
