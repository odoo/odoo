import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class PlausiblePush extends Interaction {
    static selector = ".js_plausible_push";

    setup() {
        const { eventName, eventParams } = this.el.dataset;

        window.plausible ||= function () { (window.plausible.q = window.plausible.q || []).push(arguments) };
        window.plausible(eventName, { props: eventParams || {} });
    }
}

registry
    .category("public.interactions")
    .add("website.plausible_push", PlausiblePush);
