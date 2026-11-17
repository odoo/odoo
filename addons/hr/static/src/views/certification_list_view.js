import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

export class CertificationListController extends ListController {
    setup() {
        // read by the archInfo getter, which is used in super.setup()
        this.hasCertificationSkillType = false;
        super.setup();
        onWillStart(async () => {
            this.hasCertificationSkillType = Boolean(
                await this.orm.searchCount("hr.skill.type", [["is_certification", "=", true]])
            );
        });
    }

    get archInfo() {
        return {
            ...this._archInfo,
            headerButtons: this._archInfo.headerButtons.filter(
                (button) =>
                    button.clickParams.name !== "open_hr_employee_skill_modal" ||
                    this.hasCertificationSkillType
            ),
        };
    }

    set archInfo(archInfo) {
        this._archInfo = archInfo;
    }
}

export const certificationListView = {
    ...listView,
    Controller: CertificationListController,
};

registry.category("views").add("hr_employee_skill_certification_list", certificationListView);
