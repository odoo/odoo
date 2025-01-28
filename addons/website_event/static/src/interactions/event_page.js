import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class EventPage extends Interaction {
    static selector = "#o_wevent_event_submenu .dropdown-menu a.dropdown-toggle";
    dynamicContent = {
        _root: {
            "t-on-click.stop": () => {},
        },
    };
}

registry
    .category("public.interactions")
    .add("website_event.event_page", EventPage);
