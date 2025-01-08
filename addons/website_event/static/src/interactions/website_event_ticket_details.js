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
        _envBus: {
            "t-on-websiteEvent.enableSubmit": () => this.buttonDisabled = false,
        },
        ".form-select": {
            "t-on-change": () => {}, // use updateContent() to enable/disable submit button
        },
        ".a-submit": {
            "t-on-click.prevent.stop": this.onSubmitClick,
            "t-att-disabled": () => this.noTicketsOrdered || this.buttonDisabled ? "disabled" : false,
        },
    };

    get post() {
        const post = {};
        const selectEls = this.el.querySelectorAll("select");
        selectEls.forEach((selectEl) => {
            post[selectEl.name] = selectEl.value;
        });
        return post;
    }

    get noTicketsOrdered() {
        return Object.values(this.post).every((value) => parseInt(value) === 0);
    }

    /**
     * @param {Event} ev
     */
    async onSubmitClick(ev) {
        const formEl = ev.currentTarget.closest("form");
        this.buttonDisabled = true;
        const modal = await this.waitFor(rpc(formEl.action, this.post));

        const modalEl = new DOMParser().parseFromString(modal, "text/html").body.firstChild;
        this.insert(modalEl, document.body);
    }
}

registry
    .category("public.interactions")
    .add("website_event.ticket_details", TicketDetails);
