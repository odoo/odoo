import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class EventPageOption extends Plugin {
    static id = "eventPageOption";
    evenPageSelector = "main:has(.o_wevent_event)";
    resources = {
        builder_options: [
            {
                template: "website_event.EventPageOption",
                selector: this.evenPageSelector,
                editableOnly: false,
            },
            {
                template: "website_event.EventMainPageOption",
                selector: "main:has(#o_wevent_event_main)",
                editableOnly: false,
            },
        ],
        builder_actions: this.getActions(),
    };

    setup() {
        this.orm = this.services.orm;
        this.currentWebsiteUrl = this.document.location.pathname;
        this.eventId = this.getEventObjectId();
    }

    getActions() {
        return {
            displaySubMenu: {
                isReload: true,
                getReloadUrl: () => this.eventData["website_url"],
                prepare: async () => this.loadEventData(),
                apply: async () => {
                    await this.toggleWebsiteMenu("true");
                    return { reloadUrl: this.eventData["website_url"] };
                },
                clean: async () => {
                    await this.toggleWebsiteMenu("");
                },
                isApplied: () => this.eventData["website_menu"],
            },
        };
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
        const isEventPage = this.editable.querySelector(this.evenPageSelector);
        if (!isEventPage) {
            return 0;
        }
        const objectIds = this.currentWebsiteUrl.match(/\d+(?![-\w])/);
        return parseInt(objectIds[0]) | 0;
    }
}

registry.category("website-plugins").add(EventPageOption.id, EventPageOption);
