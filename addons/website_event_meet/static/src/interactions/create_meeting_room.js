import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { rpc } from "@web/core/network/rpc";

export class CreateMeetingRoom extends Interaction {
    static selector = ".o_wevent_create_room_button";
    dynamicContent = {
        _root: { "t-on-click": this.onCreateRoomClick }
    };

    async onCreateRoomClick() {
        if (!this.createModalEl) {
            const langs = await this.waitFor(rpc("/event/active_langs"));
            if (langs) {
                this.createModalEl = this.renderAt("event_meet_create_room_modal", {
                    csrf_token: odoo.csrf_token,
                    eventId: this.el.dataset.eventId,
                    defaultLangCode: this.el.dataset.defaultLangCode,
                    langs: langs,
                }, this.el, "afterend")[0];
            }
        }
        if (this.createModalEl) {
            Modal.getOrCreateInstance(this.createModalEl).show();
        }
    }
}

registry
    .category("public.interactions")
    .add("website_event_meet.create_meeting_room", CreateMeetingRoom);
