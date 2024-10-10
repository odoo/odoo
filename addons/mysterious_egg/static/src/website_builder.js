import { Component, onWillStart, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Editor } from "@html_editor/editor";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { LazyComponent } from "@web/core/assets";

export const unslugHtmlDataObject = (repr) => {
    const match = repr && repr.match(/(.+)\((\d+),(.*)\)/);
    if (!match) {
        return null;
    }
    return {
        model: match[1],
        id: match[2] | 0,
    };
};

class WebsiteBuilder extends Component {
    static template = "mysterious_egg.WebsiteBuilder";
    static components = { LazyComponent };

    setup() {
        this.orm = useService("orm");
        this.websiteContent = useRef("iframe");
        onWillStart(async () => {
            const slugCurrentWebsite = await this.orm.call("website", "get_current_website");
            this.backendWebsiteId = unslugHtmlDataObject(slugCurrentWebsite).id;
            this.initialUrl = `/website/force/${encodeURIComponent(this.backendWebsiteId)}`;
        });

        this.editor = new Editor(
            {
                Plugins: [...MAIN_PLUGINS],
            },
            this.env.services
        );
    }

    onWebsiteLoaded() {
        this.editor.attachTo(this.websiteContent.el.contentDocument.body);
    }
}

registry.category("actions").add("egg_website_preview", WebsiteBuilder);
