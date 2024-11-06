import { registry } from "@web/core/registry";
import { Interaction } from "@website/core/interaction";

export class PlausiblePush extends Interaction {
    static selector = ".js_plausible_push";

    setup() {
        const { eventName, eventParams } = this.el.dataset;

        window.plausible =
            window.plausible ||
            function () {
                (window.plausible.q = window.plausible.q || []).push(arguments);
            };
        window.plausible(eventName, { props: eventParams || {} });
    }
}

registry
    .category("website.active_elements")
    .add("website.plausible_push", PlausiblePush);
