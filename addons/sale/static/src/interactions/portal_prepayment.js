import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class PortalPrepayment extends Interaction {
    static selector = ".o_portal_sale_sidebar";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _amountPrepaymentButton: () => this.amountPrepaymentButton,
        _amountTotalButton: () => this.amountTotalButton,
    };
    dynamicContent = {
        _amountPrepaymentButton: {
            "t-on-click": () => this.reloadAmount(true),
            "t-att-class": () => ({ "active": this.isPartialPayment }),
        },
        _amountTotalButton: {
            "t-on-click": () => this.reloadAmount(false),
            "t-att-class": () => ({ "active": !this.isPartialPayment }),
        },
        "span[id='o_sale_portal_use_amount_prepayment']": {
            "t-att-class": () => ({ "d-none": !this.isPartialPayment }),
        },
        "span[id='o_sale_portal_use_amount_total']": {
            "t-att-class": () => ({ "d-none": this.isPartialPayment }),
        },
    };

    setup() {
        this.amountTotalButton = document.querySelector("button[name='o_sale_portal_amount_total_button']");
        this.amountPrepaymentButton = document.querySelector("button[name='o_sale_portal_amount_prepayment_button']");

        if (!this.amountTotalButton) {
            // Button not available in dom => confirmed SO or partial payment not enabled on this SO
            // this widget has nothing to manage
            return;
        }

        const params = new URLSearchParams(window.location.search);
        this.isPartialPayment = params.has('downpayment') ? params.get('downpayment') === 'true' : true;
        this.showPaymentModal = params.get('showPaymentModal') === 'true';
    }

    start() {
        // When updating the amount re-open the modal.
        if (this.showPaymentModal) {
            document.querySelector("#o_sale_portal_paynow")?.click();
        }
    }

    reloadAmount(isPartialPayment) {
        const searchParams = new URLSearchParams(window.location.search);
        searchParams.set("downpayment", isPartialPayment);
        searchParams.set("showPaymentModal", true);
        window.location.search = searchParams.toString();
    }
}

registry
    .category("public.interactions")
    .add("sale.portal_prepayment", PortalPrepayment);
