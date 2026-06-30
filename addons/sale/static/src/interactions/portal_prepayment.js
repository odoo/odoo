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
            't-on-click': () => this.reloadAmount(true),
            't-att-class': () => ({ 'active': this.isDownPayment }),
        },
        _amountTotalButton: {
            't-on-click': () => this.reloadAmount(false),
            't-att-class': () => ({ 'active': !this.isDownPayment }),
        },
        'span[id="o_sale_portal_use_amount_prepayment"]': {
            't-att-class': () => ({ 'd-none': !this.isDownPayment }),
        },
        'span[id="o_sale_portal_use_amount_total"]': {
            't-att-class': () => ({ 'd-none': this.isDownPayment }),
        },
    };

    setup() {
        this.amountPrepaymentButton = document.querySelector(
            'button[name="o_sale_portal_amount_prepayment_button"]'
        );
        this.amountTotalButton = document.querySelector(
            'button[name="o_sale_portal_amount_total_button"]'
        );
        const params = new URLSearchParams(window.location.search);
        if (params.has('amount_selection')) {
           this.isDownPayment = params.get('amount_selection') === 'down_payment'
        } else if (params.has('payment_amount')) {
            const paymentAmount = params.get('payment_amount');
            this.isDownPayment = Number(paymentAmount) < Number(this.el.dataset.orderAmountTotal);
        } else {
            this.isDownPayment = true;
        }
        this.showPaymentModal = params.has('payment_amount') || params.has('amount_selection');
    }

    start() {
        // When updating the amount re-open the modal.
        if (this.showPaymentModal) {
            document.querySelector("#o_sale_portal_paynow")?.click();
        }
    }

    reloadAmount(isDownPayment) {
        const searchParams = new URLSearchParams(window.location.search);
        searchParams.set('amount_selection', isDownPayment ? 'down_payment' : 'full_amount');
        window.location.search = searchParams.toString();
    }
}

registry
    .category("public.interactions")
    .add("sale.portal_prepayment", PortalPrepayment);
