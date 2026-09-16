import { Plugin, onWillStart, proxy, usePlugin } from "@odoo/owl";
import { user } from "@web/core/user";
import { ORM } from "@web/core/orm_plugin";

export class CertificationPlugin extends Plugin {
    state = proxy({ hasCertificationSkillType: null, isHrManager: null });

    setup() {
        const orm = usePlugin(ORM);
        onWillStart(async () => {
            [this.state.hasCertificationSkillType, this.state.isHrManager] = await Promise.all([
                orm.searchCount("hr.skill.type", [["is_certification", "=", true]]).then(Boolean),
                user.hasGroup("hr.group_hr_manager"),
            ]);
        });
    }
}
