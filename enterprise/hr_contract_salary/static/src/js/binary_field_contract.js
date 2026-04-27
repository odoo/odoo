/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { BinaryField, binaryField } from "@web/views/fields/binary/binary_field";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";

export class BinaryContractFile extends BinaryField{
    static template = "l10n_be_hr_contract_salary.BinaryContractFile";
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
    }
    async onFileDelete(){
        const dialogProps = {
            body: _t("Are you sure you want to delete this file permanently ?"),
            confirm: async () => {
                this.update({})
            },
            cancel: () => {},
        };
        this.dialogService.add(ConfirmationDialog, dialogProps);
    }
}

export const binaryContractFile = {
    ...binaryField,
    component: BinaryContractFile,
};

registry.category("fields").add("binaryContractFile", binaryContractFile);
