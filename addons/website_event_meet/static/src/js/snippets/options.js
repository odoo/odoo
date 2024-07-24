/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";
import { WebsiteEvent } from "@website_event/snippets/options";


patch(WebsiteEvent.prototype, {

    /**
     * @override
     */
    async willStart() {
        const res = await super.willStart(...arguments);
        const rpcData = await this.env.services.orm.read("event.event", [this.eventId], ["meeting_room_allow_creation"]);
        this.meetingRoomAllowCreation = rpcData[0]['meeting_room_allow_creation'];
        return res;
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    allowRoomCreation(previewMode, widgetValue, params) {
        return this.env.services.orm.write("event.event", [this.eventId], {
            meeting_room_allow_creation: widgetValue,
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'allowRoomCreation': {
                return this.meetingRoomAllowCreation;
            }
        }
        return super._computeWidgetState(...arguments);
    },
});

registerWebsiteOption("EventMeetPageOption", {
    Class: WebsiteEvent,
    selector: "main:has(.o_wemeet_container)",
    template: "website_event_meet.event_meet_page_option",
    noCheck: true,
    data: {
        string: _t("Event Page"),
        pageOptions: true,
        groups: ["website.group_website_designer"],
    },
});
