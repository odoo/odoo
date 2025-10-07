/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    copyClipboardButtonField,
    CopyClipboardButtonField,
} from "@web/views/fields/copy_clipboard/copy_clipboard_field";

import { browser } from "@web/core/browser/browser";
import { CopyButton } from "@web/core/copy_button/copy_button";
import { formatCurrency } from "@web/core/currency"
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

class PaymentWizardCopyButton extends CopyButton {
    setup() {
        super.setup();
        this.orm = useService("orm")
    }

    async onClick() {
        await this.env.model.mutex.getUnlockedDef();
        await this.logLink();
        return super.onClick();
    }

    async logLink() {
        try {
            const res_model = this.env.model.root.data.res_model;
            const res_id = this.env.model.root.data.res_id;
            const amount = this.env.model.root.data.amount;
            const currency_id = this.env.model.root.data.currency_id;
            await this.orm.call(
                res_model,
                "message_post",
                [[res_id]],
                {
                    body: _t(
                        "Payment link of %s has been generated",
                        formatCurrency(amount, currency_id.id)
                    ),
                }
            );
        } catch (error) {
            return browser.console.warn(error);
        }
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
