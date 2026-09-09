/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

const log = makeLogger("website.interaction.plausible_push");

export class PlausiblePush extends Interaction {
    static selector = ".js_plausible_push";

    setup() {
        const { eventName, eventParams } = this.el.dataset;
        log.pipeline("PlausiblePush setup: push event", () => ({
            eventName,
            eventParams,
            plausibleLoaded: !!window.plausible,
        }));

        window.plausible ||= function () {
            (window.plausible.q = window.plausible.q || []).push(arguments);
        };
        let props;
        try {
            props = JSON.parse(eventParams) || {};
        } catch {
            props = {};
        }
        window.plausible(eventName, { props });
    }
}

registry.category("public.interactions").add("website.plausible_push", PlausiblePush);
