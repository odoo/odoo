/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProjectTaskFormController } from "@project/views/project_task_form/project_task_form_controller";

patch(ProjectTaskFormController.prototype, {
	setup() {
		super.setup();
		// Remove breadcrumb of Todo which in 2nd last position
		if (!(this.env.searchModel.context.show_todo_breadcrumb ?? true)) {
            this.env.config.breadcrumbs.splice(-2, 1);
        }
	}
})
