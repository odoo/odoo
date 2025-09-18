{
    "name": "Project HR",
    "version": "1.0",
    "author": "AgroMarin",
    "summary": "Replace user assignees in project with HR employees",
    "description": """
        Bridge module that makes hr.employee the primary assignee identity
        in project.task and project.project.

        user_ids / user_id are demoted to computed stored fields (derived from
        employee_ids / employee_id) so that IR security rules and portal
        machinery continue to work without modification.

        This is an intermediate step toward a unified resource model where
        resource.resource lives in base and all workforce modules share one
        identity anchor.
    """,
    "category": "Project",
    "depends": ["project", "hr"],
    "data": [
        "views/project_task_views.xml",
        "views/project_project_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "license": "LGPL-3",
}
