import { onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { useCheckDuplicateService } from "./account_duplicate_transaction_hook";

export class AccountDuplicateTransactionsListRenderer extends ListRenderer {
    static template = "account_online_synchronization.AccountDuplicateTransactionsListRenderer";
    static recordRowTemplate = "account_online_synchronization.AccountDuplicateTransactionsRecordRow";

    setup() {
        super.setup();
        this.duplicateCheckService = useCheckDuplicateService();

        onMounted(() => {
            this.deleteButton = document.querySelector('button[name="delete_selected_transactions"]');
            this.deleteButton.disabled = true;
        });
    }

    toggleRecordSelection(selected, record) {
        this.duplicateCheckService.updateLIne(selected, record.data.id);
        this.deleteButton.disabled = this.duplicateCheckService.selectedLines.size === 0;
    }

    get hasSelectors() {
        return true;
    }

    getRowClass(record) {
        let classes = super.getRowClass(record);
        const firstIdsInGroup = this.env.model.root.data.first_ids_in_group;
        if (firstIdsInGroup instanceof Array && firstIdsInGroup.includes(record.data.id)) {
            classes += " account_duplicate_transactions_lines_list_x2many_group_line";
        }
        return classes;
    }
}

export class AccountDuplicateTransactionsLinesListX2ManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: AccountDuplicateTransactionsListRenderer,
    };
}

registry.category("fields").add("account_duplicate_transactions_lines_list_x2many", {
    ...x2ManyField,
    component: AccountDuplicateTransactionsLinesListX2ManyField,
});
