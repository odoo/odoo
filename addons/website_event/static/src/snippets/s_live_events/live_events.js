import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class LiveEvents extends Interaction {

    static selector = ".s_live_event";

    setup() {
        this.updateEvent();
    }

    async getLiveEvent() {
        const [event] = await this.services.orm.searchRead('event.event', [['is_ongoing', '=', true]], [], { limit: 1 });
        return event;
    }

    async updateEvent() {
        const event = await this.getLiveEvent();
        this.el.replaceChildren();
        this.renderAt("website_event.s_live_event_template", {
            event: event
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
