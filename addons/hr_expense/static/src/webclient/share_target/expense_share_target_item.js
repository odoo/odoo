import { registry } from "@web/core/registry";
import { ShareTargetItem } from "@web/webclient/share_target/share_target_item";
import { AbstractExpenseDocumentUpload } from "@hr_expense/mixins/document_upload";
import { _t } from "@web/core/l10n/translation";

export class ExpenseShareTargetItem extends AbstractExpenseDocumentUpload(ShareTargetItem) {
    static name = _t("Expense");
    static sequence = 1;

    async process() {
        await this._onChangeFileInput(this.getFiles());
        await this.generateOpenExpensesAction();
    }
}

registry.category("share_target_items").add("hr_expense", ExpenseShareTargetItem);
