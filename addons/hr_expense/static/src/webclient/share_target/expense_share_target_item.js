import { registry } from "@web/core/registry";
import { ShareTargetItem } from "@web/webclient/share_target/share_target_item";
import { _t } from "@web/core/l10n/translation";

export class ExpenseShareTargetItem extends ShareTargetItem {
    static name = _t("Expense");
    static sequence = 1;

    async process() {
        await this.action.doActionButton(
            {
                type: "upload",
                name: "action_create_from_uploads",
                resModel: "hr.expense",
                context: this.context,
            },
            { files: this.props.files }
        );
    }
}

registry.category("share_target_items").add("hr_expense", ExpenseShareTargetItem);
