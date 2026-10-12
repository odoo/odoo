import { usePlugin } from "@odoo/owl";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";

export class PortalInvoicePagePayment extends Interaction {
    static selector = "#portal_pay";

    setup() {
        this.bootstrap = usePlugin(BootstrapInstance);
        if (this.el.dataset.payment) {
            this.bootstrap.getOrCreateInstance(Modal, "#pay_with").show();
        }
    }
}

registry
    .category("public.interactions")
    .add("account_payment.portal_invoice_page_payment", PortalInvoicePagePayment);
