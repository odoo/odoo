import { registry } from "@web/core/registry";
import { ShareTargetItem } from "@web/webclient/share_target/share_target_item";
import { _t } from "@web/core/l10n/translation";
import { uploadFiles } from "@web/views/view_button/upload_button";

export class ExpenseShareTargetItem extends ShareTargetItem {
    static name = _t("Expense");
    static sequence = 1;

    async process() {
        const action = await uploadFiles(this.env.services, {
            clickParams: { name: "action_create_from_uploads" },
            resModel: "hr.expense",
            context: this.context,
            files: this.getFiles(),
        });
        if (action) {
            await this.action.doAction(action);
        }
    }
}

registry.category("share_target_items").add("hr_expense", ExpenseShareTargetItem);
