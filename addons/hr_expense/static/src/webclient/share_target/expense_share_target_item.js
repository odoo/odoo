import { registry } from "@web/core/registry";
import { ShareTargetItem } from "@web/webclient/share_target/share_target_item";
import { useExpenseDocumentUpload } from "@hr_expense/document_upload/document_upload";
import { _t } from "@web/core/l10n/translation";

export class ExpenseShareTargetItem extends ShareTargetItem {
    static name = _t("Expense");
    static sequence = 1;

    expenseUpload = useExpenseDocumentUpload({
        modelName: () => this.modelName,
        context: () => this.context,
    });

    get modelName() {
        return "hr.expense";
    }

    async process() {
        await this.expenseUpload.uploadFiles(this.getFiles());
        await this.expenseUpload.generateOpenExpensesAction();
    }
}

registry.category("share_target_items").add("hr_expense", ExpenseShareTargetItem);
