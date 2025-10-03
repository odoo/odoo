import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class PortalInvoicePagePayment extends Interaction {
    static selector = "#portal_pay";
    dynamicContent = {
        "#o_payment_tabs": { "t-on-shown.bs.tab": this.onTabChanged }
    };

    setup() {
        if (this.el.dataset.payment) {
            (new Modal("#pay_with")).show();
        }
    }

    onTabChanged(ev) {
        const activeTabId = ev.target.id;
        const providersInput = document.querySelector("input[name='providers_by_amount']");
        if (!providersInput) {
            return;
        }
        const providersByAmount = JSON.parse(providersInput.value);

        let availableProviders = [];
        if (activeTabId === "o_payment_installments_tab") {
            availableProviders = providersByAmount.next_amount || [];
        } else if (activeTabId === "o_payment_full_tab") {
            availableProviders = providersByAmount.total || [];
        }

        let firstVisibleSet = false;

        document.querySelectorAll("li[name='o_payment_option']").forEach(li => {
            const input = li.querySelector("input[name='o_payment_radio'][data-provider-id]");
            if (!input) {
                return;
            }

            const providerId = parseInt(input.dataset.providerId, 10);

            if (availableProviders.includes(providerId)) {
                li.classList.add("list-group-item"); // fix list corner radius
                li.classList.remove("d-none");

                if (!firstVisibleSet) {
                    input.checked = true;
                    firstVisibleSet = true;

                    input.dispatchEvent(new Event("change", { bubbles: true }));
                }
            } else {
                li.classList.remove("list-group-item"); // fix list corner radius
                li.classList.add("d-none");
                input.checked = false;
            }
        });
    }
}

registry
    .category("public.interactions")
    .add("account_payment.portal_invoice_page_payment", PortalInvoicePagePayment);
