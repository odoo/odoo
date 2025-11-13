import { hrPresenceStatus, HrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(HrPresenceStatus.prototype, {
    get label() {
        if (this.value === 'presence_present') {
            const hasUser = this.props.record.data.user_id;
            if (!hasUser) {
                return _t("Present (untracked)");
            }
        } else if (this.value === 'presence_out_of_working_hour') {
            return _t("Off-Hours");
        }
        
        return super.label;
    }
});

Object.assign(hrPresenceStatus, {
    fieldDependencies: [
        ...hrPresenceStatus.fieldDependencies,
        { name: "user_id", type: "many2one" },
    ],
});
