import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";

export class EventPageOptionPlugin extends Plugin {
    static id = "eventPageOption";
    resources = {
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
        const isEventPage = this.editable.querySelector("main:has(.o_wevent_event)");
        if (!isEventPage) {
            return 0;
        }
        const objectIds = this.currentWebsiteUrl.match(/\d+(?=\/|$)/);
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
