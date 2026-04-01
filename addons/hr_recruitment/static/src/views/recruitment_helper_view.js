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
            const categoryTags = await this.orm.searchRead("hr.applicant.category", [], ["name"]);
            const demoTag = categoryTags.filter((tag) => tag.name === "Demo");
            this.state.hasDemoData = demoTag.length === 1;
            this.isRecruitmentUser = await user.hasGroup("hr_recruitment.group_hr_recruitment_user");
        });
    }

    loadRecruitmentScenario() {
        this.actionService.doAction("hr_recruitment.action_load_demo_data");
    }

    actionCreateJobPosition() {
        this.actionService.doAction("hr.action_create_job_position")
    }
}
