import { Component, onMounted, onWillStart, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { BuilderMenu } from "./builder_menu";
import { Editor } from "@html_editor/editor";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";

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

class WebsitePreview extends Component {
    static template = "mysterious_egg.WebsitePreview";
    static components = { BuilderMenu };

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
        debugger;
        this.editor.attachTo(this.websiteContent.el.contentDocument.body);
    }
}

registry.category("actions").add("egg_website_preview", WebsitePreview);
