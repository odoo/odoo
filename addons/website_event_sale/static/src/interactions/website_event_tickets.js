import { _t } from "@web/core/l10n/translation";
import { Tickets } from '@website_event/interactions/website_event_tickets';
import { patch } from "@web/core/utils/patch";
import { patchDynamicContent } from "@web/public/utils";
import { session } from "@web/session";

patch(Tickets.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            ".form-select": { "t-on-change": this.updateConfirmationButtonTextContent.bind(this) },
        });
    },

    /**
     * If the event has free and paying tickets, the label of the confirm button is "Confirm Registration"
     * because checkout may not be required. It must be updated if the user select a paying ticket.
     */
    updateConfirmationButtonTextContent() {
        const confirmButtonEl = this.el.querySelector(".o_wevent_registration_confirm");
        if (!confirmButtonEl) {
            return;
        }
        const selectedPayingTickets = Array.from(this.el.querySelectorAll(".o_wevent_ticket_selector")).filter(
            (ticket) => ticket.querySelector("select").value > 0 && ticket.querySelector(".oe_currency_value")
        )
        if (this.el.dataset.accountOnCheckout == "mandatory" && session.is_public && selectedPayingTickets.length > 0) {
            confirmButtonEl.textContent = _t("Sign In");
        }
        else if (selectedPayingTickets.length > 0) {
            confirmButtonEl.textContent = _t("Go to Payment");
        }
        else {
            confirmButtonEl.textContent = _t("Confirm Registration");
        }
    },
});
