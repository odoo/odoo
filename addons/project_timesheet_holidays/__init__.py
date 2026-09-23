from odoo import Command

from . import models


def post_init(env):
    type_ids_ref = env.ref(
        "hr_timesheet.internal_project_default_stage", raise_if_not_found=False
    )
    type_ids = [Command.link(type_ids_ref.id)] if type_ids_ref else []
    companies = env["res.company"].search(
        [
            "|",
            ("hr_timesheet_config_id.internal_project_id", "=", False),
            (
                "project_timesheet_holidays_config_id.leave_timesheet_task_id",
                "=",
                False,
            ),
        ]
    )
    internal_projects_by_company_dict = None
    project = env["project.project"]
    for company in companies:
        company = company.with_company(company)
        if not company.hr_timesheet_config_id.internal_project_id:
            if not internal_projects_by_company_dict:
                internal_projects_by_company_read = project.search_read(  # noqa: E8507 - computed once, on first need
                    [
                        ("name", "=", env._("Internal")),
                        ("allow_timesheets", "=", True),
                        ("company_id", "in", companies.ids),
                    ],
                    ["company_id", "id"],
                )
                internal_projects_by_company_dict = {
                    res["company_id"][0]: res["id"]
                    for res in internal_projects_by_company_read
                }
            project_id = internal_projects_by_company_dict.get(company.id, False)
            if not project_id:
                project_id = project.create(
                    {
                        "name": env._("Internal"),
                        "allow_timesheets": True,
                        "company_id": company.id,
                        "type_ids": type_ids,
                    }
                ).id
            company.write({"internal_project_id": project_id})
        if not company.project_timesheet_holidays_config_id.leave_timesheet_task_id:
            task = company.env["project.task"].create(
                {
                    "name": env._("Time Off"),
                    "project_id": company.hr_timesheet_config_id.internal_project_id.id,
                    "active": True,
                    "company_id": company.id,
                }
            )
            company.write(
                {
                    "leave_timesheet_task_id": task.id,
                }
            )
