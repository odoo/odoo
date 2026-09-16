import { providePlugins, usePlugin } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";
import { CertificationPlugin } from "./certification_plugin";

export class CertificationListController extends ListController {
    setup() {
        providePlugins([CertificationPlugin]);
        this.certificationState = usePlugin(CertificationPlugin).state;
        super.setup();
    }

    get archInfo() {
        return {
            ...this._archInfo,
            headerButtons: this._archInfo.headerButtons.filter(
                (button) =>
                    button.clickParams.name !== "open_hr_employee_skill_modal" ||
                    this.certificationState.hasCertificationSkillType
            ),
        };
    }

    set archInfo(archInfo) {
        this._archInfo = archInfo;
    }
}

export class CertificationListRenderer extends ListRenderer {
    static template = "hr_skills.CertificationListRenderer";

    setup() {
        super.setup();
        this.certificationState = usePlugin(CertificationPlugin).state;
    }
}

export const certificationListView = {
    ...listView,
    Controller: CertificationListController,
    Renderer: CertificationListRenderer,
};

registry.category("views").add("hr_employee_skill_certification_list", certificationListView);
