import { addLoadingEffect } from '@web/core/utils/ui';
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class Tickets extends Interaction {
    static selector = ".o_wevent_js_tickets";
    dynamicContent = {
        _root: { "t-on-submit": this.onSubmit },
        ".form-select": {
            "t-on-change": () => {}, // use updateContent() to enable/disable submit button
        },
        ".a-submit": {
            "t-att-disabled": () => this.noTicketsOrdered,
        },
    };

    get noTicketsOrdered() {
        return Boolean(
            !Array.from(this.el.querySelectorAll("select").values()).find(
                (select) => select.value > 0
            )
        );
    }

    /**
     * Avoid submitting the form and display an error message if the number of seats ordered
     * is greater than the number of seats available. This check is performed with js to
     * prevents users from losing their inputs and it is also done in the controller for
     * security reasons.
     *
     * @param {MouseEvent} ev
     */
    onSubmit(ev) {
        // The seats availability check is done by the controller in any case. So if the form submission
        // does not confirm registration or if the number of available seats is not present, the
        // verification can be skipped.
        console.log("in Class");
        console.log(this.el.classList.contains("o_wevent_js_ticket_details"));
        if (this.el.classList.contains("o_wevent_js_ticket_details")) {
            return;
        }
        const removeLoadingEffect = addLoadingEffect(this.el.querySelector("button[type='submit']"));
        if (!this.el.dataset.seatsAvailable) {
            return;
        }
        try {
            ev.preventDefault();
            const seatsAvailable = parseInt(this.el.dataset.seatsAvailable);
            let seatsOrdered = 0;
            for (const seatQuantity of this.el.querySelectorAll("select")) {
                seatsOrdered += parseInt(seatQuantity.value);
                if (seatsOrdered > seatsAvailable) {
                    removeLoadingEffect();
                    throw new Error("More ordered tickets than available seats.");
                }
            }
            this.el.submit();
        }
        catch {
            this.renderAt("website_event.registration_insufficient_seats_error", {}, document.body);
        }
    }
}

registry
    .category("public.interactions")
    .add("website_event.tickets", Tickets);
