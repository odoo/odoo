import { ShareTargetItem } from "@web/webclient/share_target/share_target_item";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class HrHolidaysShareTargetItem extends ShareTargetItem {
    static name = _t("Time Off");
    static sequence = 3;

    get modelName() {
        return "hr.leave";
    }
}
registry.category("share_target_items").add("hr_holidays", HrHolidaysShareTargetItem);
