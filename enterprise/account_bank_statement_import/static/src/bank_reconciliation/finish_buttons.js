/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { AccountFileUploader } from "@account/components/account_file_uploader/account_file_uploader";
import { BankRecFinishButtons } from "@account_accountant/components/bank_reconciliation/finish_buttons";

patch(BankRecFinishButtons, {
    components: {
        AccountFileUploader,
    }
})
