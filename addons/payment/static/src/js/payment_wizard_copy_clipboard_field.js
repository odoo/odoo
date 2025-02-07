/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    copyClipboardButtonField,
    CopyClipboardButtonField,
} from "@web/views/fields/copy_clipboard/copy_clipboard_field";

import { CopyButton } from "@web/core/copy_button/copy_button";

class PaymentWizardCopyButton extends CopyButton {
    async onClick() {
        await this.env.model.mutex.getUnlockedDef();
        return super.onClick();
    }
}

class PaymentWizardCopyClipboardButtonField extends CopyClipboardButtonField {
    static components = { CopyButton: PaymentWizardCopyButton };
}

const paymentWizardCopyClipboardButtonField = {
    ...copyClipboardButtonField,
    component: PaymentWizardCopyClipboardButtonField,
};

registry
    .category("fields")
    .add("PaymentWizardCopyClipboardButtonField", paymentWizardCopyClipboardButtonField);
