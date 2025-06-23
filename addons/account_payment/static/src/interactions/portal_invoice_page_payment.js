import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class PortalInvoicePagePayment extends Interaction {
    static selector = "#portal_pay";

    dynamicContent = {
        ".o_btn_payment_tab": {
            "t-on-shown.bs.tab": this._onChangePaymentTabs,
        },
    };

    setup() {
        if (this.el.dataset.payment) {
            (new Modal("#pay_with")).show();
        }
    };

    /**
     * Handles payment tab changes (installment or full amount).
     *
     * This method listens for the `shown.bs.tab` event on payment tab buttons.
     * When the user switches tabs, it updates the URL parameters `mode` and
     * `render_change`, then reloads the page. This forces the backend to
     * re-render the payment form with updated data, including the corresponding
     * amount and available payment providers.
     *
     * Added URL parameters:
     * - mode: either 'installment' or 'full', depending on the selected tab.
     * - render_change: 'true', indicating that the change should trigger a re-render.
     */
    _onChangePaymentTabs(event) {
        const activatedTab = event.target.id;
        const mode =
            activatedTab === "o_payment_installments_tab"
                ? "installment"
                : activatedTab === "o_payment_full_tab"
                ? "full"
                : null;

        if (mode) {
            const searchParams = new URLSearchParams(window.location.search);
            searchParams.set("mode", encodeURIComponent(mode));
            searchParams.set("render_change", true);
            searchParams.set("payment", true);
            window.location.search = searchParams.toString();
        }
    }
}

registry
    .category("public.interactions")
    .add("account_payment.portal_invoice_page_payment", PortalInvoicePagePayment);
