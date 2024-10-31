import { Component, useAttachedEl } from "@odoo/owl";
import { registry } from "@web/core/registry";

class PlausiblePush extends Component {
    static selector = ".js_plausible_push";
    
    setup() {
        const el = useAttachedEl();
        const {eventName, eventParams} = el.dataset;

        window.plausible = window.plausible || function () {
            (window.plausible.q = window.plausible.q || []).push(arguments);
        };
        window.plausible(eventName, {props: eventParams || {}});
    }
}

registry.category("website.active_elements").add("website.plausible_push", PlausiblePush);

