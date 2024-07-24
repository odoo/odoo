/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { SnippetOption } from "@web_editor/js/editor/snippets.options";
import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";

export class WebsiteEvent extends SnippetOption {

    /**
     * @override
     */
    async willStart() {
        const res = await super.willStart(...arguments);
        this.currentWebsiteUrl = this.ownerDocument.location.pathname;
        this.eventId = this._getEventObjectId();
        // Only need for one RPC request as the option will be destroyed if a
        // change is made.
        const rpcData = await this.env.services.orm.read("event.event", [this.eventId], ["website_menu","website_url"]);
        this.data.reload = this.currentWebsiteUrl;
        this.websiteMenu = rpcData[0]['website_menu'];
        this.data.reload = rpcData[0]['website_url'];
        return res;
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    displaySubmenu(previewMode, widgetValue, params) {
        return this.env.services.orm.call("event.event", "toggle_website_menu", [[this.eventId], widgetValue]);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'displaySubmenu': {
                return this.websiteMenu;
            }
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * Ensure that we get the event object id as we could be inside a sub-object of the event
     * like an event.track
     * @private
     */
    _getEventObjectId() {
        const objectIds = this.currentWebsiteUrl.match(/\d+(?![-\w])/);
        return parseInt(objectIds[0]) | 0;
    }
}

registerWebsiteOption("EventsPageOption", {
    selector: "main:has(.o_wevent_events_list)",
    template: "website_event.events_page_option",
    noCheck: true,
    data: {
        string: _t("Events Page"),
        pageOptions: true,
        groups: ["website.group_website_designer"],
    },
});

registerWebsiteOption("EventPageOption", {
    Class: WebsiteEvent,
    selector: "main:has(.o_wevent_event)",
    template: "website_event.event_page_option",
    noCheck: true,
    data: {
        string: _t("Event Page"),
        pageOptions: true,
        groups: ["website.group_website_designer"],
    },
});

registerWebsiteOption("EventCoverPositionOption", {
    Class: WebsiteEvent,
    selector: "main:has(#o_wevent_event_main)",
    template: "website_event.cover_position_option",
    noCheck: true,
    data: {
        string: _t("Event Cover Position"),
        groups: ["website.group_website_designer"],
    },
});
