/** @odoo-module */
import { patch } from "@web/core/utils/patch";

import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

import { ResumeX2ManyField, ResumeListRenderer } from "@hr_skills/fields/resume_one2many/resume_one2many";

patch(ResumeX2ManyField.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
        onWillStart(async () => {
            this.eventTypeId = await this.orm.call("hr.resume.line", "get_event_type_id");
        })
    },

    async onAdd ({context, editable} = {}) {
        if (context.default_line_type_id == this.eventTypeId) {
            await this.action.doAction(
                "event_hr_skills.action_resume_select_event",
                {
                    additionalContext: { active_employee_id: this.props.record.resId },
                    onClose: () => {
                        this.props.record.model.load();
                    },
                },
            );
            return;
        }
        return super.onAdd({context, editable});
    },
});

patch(ResumeListRenderer.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        onWillStart(async () => {
            this.eventTypeId = await this.orm.call("hr.resume.line", "get_event_type_id");
        })
    },

    get hasEventLines() {
        return Object.entries(this.groupedList).some((group) => (group[1].id == this.eventTypeId));
    },
});
