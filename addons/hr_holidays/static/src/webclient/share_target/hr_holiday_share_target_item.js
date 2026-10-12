import { ShareTargetItem } from "@web/webclient/share_target/share_target_item";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class HrHolidaysShareTargetItem extends ShareTargetItem {
    static name = _t("Time Off");
    static sequence = 3;

    get modelName() {
        return "hr.leave";
    }

    async process() {
        const attachments = await this.uploadAttachments();
        await this.action.doAction({
            title: _t("New Time Off"),
            type: "ir.actions.act_window",
            res_model: this.modelName,
            views: [[false, "form"]],
            context: {
                ...this.context,
                default_attachment_ids: attachments.map((a) => a.id),
            },
        });
    }
}
registry.category("share_target_items").add("hr_holidays", HrHolidaysShareTargetItem);
