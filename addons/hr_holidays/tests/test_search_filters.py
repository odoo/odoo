from datetime import date

from lxml import etree

from odoo.tests import tagged
from odoo.tools.safe_eval import safe_eval

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged("search_filters")
class TestLeaveSearchFilters(TestHrHolidaysCommon):
    """The search view is the only place a filter can be reached from, so each
    test resolves the filter's domain out of the arch by name rather than
    restating it: a filter that is renamed or dropped fails here."""

    def _filter_domain(self, view_xmlid, filter_name):
        arch = etree.fromstring(self.env.ref(view_xmlid).arch)
        nodes = arch.xpath(f"//filter[@name='{filter_name}']")
        self.assertTrue(nodes, f"the search view has no filter named {filter_name!r}")
        return nodes[0].get("domain")

    def test_missing_document_filter(self):
        """Requests whose type asks for a supporting document but that carry
        no attachment can be isolated from the search view."""
        needs_document, plain = self.env["hr.leave.type"].create(
            [
                {
                    "name": "Sick Leave",
                    "requires_allocation": False,
                    "support_document": True,
                },
                {
                    "name": "Unpaid Leave",
                    "requires_allocation": False,
                    "support_document": False,
                },
            ]
        )
        # one leave per day: two requests of the same employee may not overlap
        missing, documented, not_required = self.env["hr.leave"].create(
            [
                {
                    "name": "Missing the certificate",
                    "holiday_status_id": needs_document.id,
                    "employee_id": self.employee_emp_id,
                    "request_date_from": date(2026, 3, 11),
                    "request_date_to": date(2026, 3, 11),
                },
                {
                    "name": "Certificate attached",
                    "holiday_status_id": needs_document.id,
                    "employee_id": self.employee_emp_id,
                    "request_date_from": date(2026, 3, 12),
                    "request_date_to": date(2026, 3, 12),
                },
                {
                    "name": "No certificate asked for",
                    "holiday_status_id": plain.id,
                    "employee_id": self.employee_emp_id,
                    "request_date_from": date(2026, 3, 13),
                    "request_date_to": date(2026, 3, 13),
                },
            ]
        )
        # what an upload through the form's attachment widget leaves behind
        self.env["ir.attachment"].create(
            {
                "name": "certificate.pdf",
                "datas": b"Zm9v",
                "res_model": "hr.leave",
                "res_id": documented.id,
            }
        )
        self.assertTrue(documented.attachment_ids, "sanity: the leave carries the file")

        domain = self._filter_domain(
            "hr_holidays.view_hr_holidays_filter", "missing_document"
        )
        found = self.env["hr.leave"].search(
            [("id", "in", (missing | documented | not_required).ids)]
            + safe_eval(domain)
        )
        self.assertEqual(
            found,
            missing,
            "only the request whose type asks for a document and has none should match",
        )

    def test_active_employee_filter_defaults_on(self):
        """Allocations of archived employees stay out of the way by default,
        and can still be listed on demand."""
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Allocated Time Off",
                "requires_allocation": True,
                "allocation_validation_type": "no_validation",
            }
        )
        leaver = self.env["hr.employee"].create(
            {"name": "Gone Employee", "company_id": self.company.id}
        )
        staying, left = self.env["hr.leave.allocation"].create(
            [
                {
                    "name": "still here",
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": leave_type.id,
                    "number_of_days": 5,
                },
                {
                    "name": "already gone",
                    "employee_id": leaver.id,
                    "holiday_status_id": leave_type.id,
                    "number_of_days": 5,
                },
            ]
        )
        leaver.active = False

        action = self.env.ref(
            "hr_holidays.hr_leave_allocation_action_approve_department"
        )
        context = safe_eval(action.context)
        self.assertIn(
            "search_default_active_employee",
            context,
            "the allocations action should open on active employees only",
        )
        self.assertEqual(
            context.get("search_default_my_team"),
            1,
            "the filters the action already opened with must survive",
        )
        self.assertEqual(context.get("search_default_approve"), 2)

        scope = [("id", "in", (staying | left).ids)]
        Allocation = self.env["hr.leave.allocation"]
        self.assertEqual(
            Allocation.search(
                scope
                + safe_eval(
                    self._filter_domain(
                        "hr_holidays.view_hr_leave_allocation_filter",
                        "active_employee",
                    )
                )
            ),
            staying,
        )
        self.assertEqual(
            Allocation.search(
                scope
                + safe_eval(
                    self._filter_domain(
                        "hr_holidays.view_hr_leave_allocation_filter",
                        "archived_employee",
                    )
                )
            ),
            left,
        )
