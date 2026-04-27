import { CopyButton } from "@web/core/copy_button/copy_button";
import { registry } from "@web/core/registry";
import { CopyClipboardURLField, copyClipboardURLField } from "@web/views/fields/copy_clipboard/copy_clipboard_field"

import { HrContractSalaryUrlField } from "./url_field";

export class HrContractSalaryCopyClipboardURLField extends CopyClipboardURLField {
    static components = { Field: HrContractSalaryUrlField, CopyButton };
}

export const hrContractSalaryCopyClipboardURLField = {
    ...copyClipboardURLField,
    component: HrContractSalaryCopyClipboardURLField,
};

registry.category("fields").add("HrContractSalaryCopyClipboardURL", hrContractSalaryCopyClipboardURLField);