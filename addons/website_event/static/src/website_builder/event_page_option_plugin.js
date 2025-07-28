import { EVENT_PAGE, EVENT_PAGE_MAIN } from "@website_event/website_builder/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class EventPageOption extends BaseOptionComponent {
    static template = "website_event.EventPageOption";
    static selector = "main:has(.o_wevent_event)";
    static title = _t("Event Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

export class EventMainPageOption extends BaseOptionComponent {
    static template = "website_event.EventMainPageOption";
    static selector = "main:has(#o_wevent_event_main)";
    static title = _t("Event Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

export class EventPageOptionPlugin extends Plugin {
    static id = "eventPageOption";
    resources = {
        builder_options: [
            withSequence(EVENT_PAGE, EventPageOption),
            withSequence(EVENT_PAGE_MAIN, EventMainPageOption),
        ],
        builder_actions: {
            DisplaySubMenuAction,
        },
    };
}

export class DisplaySubMenuAction extends BuilderAction {
    static id = "displaySubMenu";
    setup() {
        this.orm = this.services.orm;
        this.currentWebsiteUrl = this.document.location.pathname;
        this.eventId = this.getEventObjectId();
        this.reload = {
            getReloadUrl: () => this.eventData["website_url"],
        }
    }

    async toggleWebsiteMenu(value) {
        await this.orm.call("event.event", "toggle_website_menu", [[this.eventId], value]);
    }

    async loadEventData() {
        if (this.eventData) {
            return;
        }
        this.eventData = (
            await this.orm.read("event.event", [this.eventId], ["website_menu", "website_url"])
        )[0];
    }

    getEventObjectId() {
        const isEventPage = this.editable.querySelector(EventPageOption.selector);
        if (!isEventPage) {
            return 0;
        }
        const objectIds = this.currentWebsiteUrl.match(/\d+(?=\/|$)/);;
        return parseInt(objectIds[0]) | 0;
    }

    async prepare() {
        return this.loadEventData();
    }

    async apply() {
        await this.toggleWebsiteMenu("true");
        return { reloadUrl: this.eventData["website_url"] };
    }

    async clean() {
        await this.toggleWebsiteMenu("");
    }

    isApplied() {
        return this.eventData["website_menu"];
    }
}

registry.category("website-plugins").add(EventPageOptionPlugin.id, EventPageOptionPlugin);
