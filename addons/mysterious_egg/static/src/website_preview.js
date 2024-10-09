import { Component, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { BuilderMenu } from "./builder_menu";

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
        onWillStart(async () => {
            const slugCurrentWebsite = await this.orm.call("website", "get_current_website");
            this.backendWebsiteId = unslugHtmlDataObject(slugCurrentWebsite).id;
            this.initialUrl = `/website/force/${encodeURIComponent(this.backendWebsiteId)}`;
        });
    }
}

registry.category("actions").add("egg_website_preview", WebsitePreview);
