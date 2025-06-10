import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class TicketDetails extends Interaction {
    static selector = ".o_wevent_js_ticket_details";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _envBus: () => this.env.bus,
    };
    dynamicContent = {
        _root: { "t-on-submit.prevent": this.onSubmit },
        _envBus: {
            "t-on-websiteEvent.enableSubmit": () => this.buttonDisabled = false,
        },
        ".a-submit": {
            "t-att-disabled": () => this.buttonDisabled ? "disabled" : false,
        },
    };

    /**
     * Allow users to submit details for their registrations.
     */
    async onSubmit() {
        this.buttonDisabled = true;
        const response = await this.waitFor(rpc(
            this.el.action,
            Object.fromEntries(new FormData(this.el)),
        ));
        if (response.status == "success") {
            const modalEl = new DOMParser().parseFromString(response.content, "text/html").body.firstChild;
            this.insert(modalEl, document.body);
        }
        else if (response.status == "error" && response.error == "no_availability") {
            this.renderAt("website_event.registration_insufficient_seats_error", {}, document.body);
        }
    }
}

registry
    .category("public.interactions")
    .add("website_event.ticket_details", TicketDetails);
