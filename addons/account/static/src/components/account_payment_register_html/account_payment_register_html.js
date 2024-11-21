import {HtmlField, htmlField} from "@web_editor/js/backend/html_field";
import {registry} from "@web/core/registry";

export class AccountPaymentRegisterHtmlField extends HtmlField {
    static template = "account.AccountPaymentRegisterHtmlField";

    async switchInstallmentsAmount(ev) {
        if (ev.srcElement.classList.contains("installments_switch_button")) {
            const root = this.env.model.root;
            await root.update({amount: root.data.installments_switch_amount});
        }
    }
}

export const accountPaymentRegisterHtmlField = {
    ...htmlField,
    component: AccountPaymentRegisterHtmlField,
};

registry.category("fields").add("account_payment_register_html", accountPaymentRegisterHtmlField);
