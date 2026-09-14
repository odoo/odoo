/** @odoo-module native */
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Component, onWillStart, useState } from "@odoo/owl";

export class RecruitmentActionHelper extends Component {
    static template = "hr_recruitment.RecruitmentActionHelper";
    static props = ["noContentHelp"];
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            hasDemoData: false,
        });
        onWillStart(async () => {
            // Keyed on the scenario's xml id rather than on a tag named "Demo":
            // the old check read every applicant category on each empty-view
            // render and then required exactly one match, so a tag a user named
            // "Demo" both faked a loaded scenario and, alongside the real one,
            // hid it.
            const [hasDemoData, isRecruitmentUser] = await Promise.all([
                this.orm.call("hr.job", "is_recruitment_scenario_loaded", []),
                user.hasGroup("hr_recruitment.group_hr_recruitment_user"),
            ]);
            this.state.hasDemoData = hasDemoData;
            this.isRecruitmentUser = isRecruitmentUser;
        });
    }

    loadRecruitmentScenario() {
        this.actionService.doAction("hr_recruitment.action_load_demo_data");
    }

    actionCreateJobPosition() {
        this.actionService.doAction("hr.action_create_job_position");
    }
}
