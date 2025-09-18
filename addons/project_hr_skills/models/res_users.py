# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# res.users.employee_skill_ids was a bridge field that enabled the chain:
#   project.task.user_ids (res.users) → employee_skill_ids → hr.employee.skill
#
# Since project_hr makes employee_ids (hr.employee) the primary task assignee
# identity, the bridge is no longer needed. user_skill_ids now reads directly
# from employee_ids.employee_skill_ids. File kept to document the removal.
