import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class LiveEvents extends Interaction {

    static selector = ".s_live_event";

    setup() {
        this.updateEvent();
    }

    async updateEvent() {
        const [event] = await rpc("/event/get_live_event");
        const background_image = JSON.parse(event.cover_properties)['background-image']
        this.el.replaceChildren();
        this.renderAt("website_event.s_live_event_template", {
            event: event,
            background_image: background_image,
        }, this.el);
    }
}

registry
    .category("public.interactions")
    .add("website_event.live_events", LiveEvents);

registry
    .category("public.interactions.edit")
    .add("website_event.live_events", {
        Interaction: LiveEvents,
    });
