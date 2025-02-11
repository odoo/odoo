import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class PortalPrepayment extends Interaction {
    static selector = ".o_portal_sale_sidebar";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _amountPrepaymentButton: () => this.amountPrepaymentButton,
        _amountTotalButton: () => this.amountPrepaymentButton,
    };
    dynamicContent = {
        _amountPrepaymentButton: {
            "t-on-click": this.onAmountPrepaymentButtonClick,
            "t-att-class": () => ({ "active": this.isPartialPayment }),
        },
        _amountTotalButton: {
            "t-on-click": this.onAmountTotalButtonClick,
            "t-att-class": () => ({ "active": !this.isPartialPayment }),
        },
        "span[id='o_sale_portal_use_amount_prepayment'], span[id='o_sale_portal_use_amount_total']": {
            "t-att-style": () => ({
                "transition-duration": "400ms",
                "transition-property": "opacity",
            }),
        },
        "span[id='o_sale_portal_use_amount_prepayment']": {
            "t-att-style": () => ({ "opacity": this.displayTotal ? 0 : 1 }),
        },
        "span[id='o_sale_portal_use_amount_total']": {
            "t-att-style": () => ({ "opacity": this.displayTotal ? 1 : 0 }),
        },
    };

    start() {
        this.amountTotalButton = document.querySelector("button[name='o_sale_portal_amount_total_button']");
        this.amountPrepaymentButton = document.querySelector("button[name='o_sale_portal_amount_prepayment_button']");

        if (!this.amountTotalButton) {
            // Button not available in dom => confirmed SO or partial payment not enabled on this SO
            // this widget has nothing to manage
            return;
        }

        const params = new URLSearchParams(window.location.search);
        this.isPartialPayment = !(params.has('downpayment') ? params.get('downpayment') === 'true' : true);
        this.displayTotal = !this.isPartialPayment;
        const showPaymentModal = params.get('showPaymentModal') === 'true';

        // When updating the amount re-open the modal.
        if (showPaymentModal) {
            this.querySelector("#o_sale_portal_paynow")?.click();
        }
    }

    onAmountPrepaymentButtonClick() {
        this.isPartialPayment = true;
        this.reloadAmount();
    }

    onAmountTotalButtonClick() {
        this.isPartialPayment = false;
        this.reloadAmount();
    }

    reloadAmount() {
        const searchParams = new URLSearchParams(window.location.search);
        searchParams.set("downpayment", this.isPartialPayment);
        searchParams.set("showPaymentModal", true);
        window.location.search = searchParams.toString();
    }
}

registry
    .category("public.interactions")
    .add("sale.portal_prepayment", PortalPrepayment);
