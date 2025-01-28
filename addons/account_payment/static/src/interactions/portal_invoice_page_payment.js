import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class PortalInvoicePagePayment extends Interaction {
    static selector = "#portal_pay";

    setup() {
        if (this.el.dataset.payment) {
            (new Modal("#pay_with")).show();
        }
    }
}

registry
    .category("public.interactions")
    .add("account_payment.portal_invoice_page_payment", PortalInvoicePagePayment);
