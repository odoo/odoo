import { MegaMenuOptionPlugin } from "@website/builder/plugins/options/mega_menu_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { BuilderAction } from "@html_builder/core/builder_action";

patch(MegaMenuOptionPlugin.prototype, {
    getTemplatePrefix(editingEl, toggle) {
        const hasSaleClass = editingEl.classList.contains("fetchEcomCategories");
        const fetchWebsiteSale = toggle ? !hasSaleClass : hasSaleClass;
        if (fetchWebsiteSale) {
            return "website_sale.";
        }
        return super.getTemplatePrefix(editingEl);
    },
});

class WebsiteSaleMegaMenuOptionPlugin extends Plugin {
    static id = "websiteSaleMegaMenuOptionPlugin";
    static dependencies = [
        "builderOptions",
        "customizeWebsite",
        "history",
        "megaMenuOptionPlugin",
    ];
    resources = {
        builder_actions: {
            ToggleFetchEcomCategoriesAction,
        },
    };
}

export class ToggleFetchEcomCategoriesAction extends BuilderAction {
    static id = "toggleFetchEcomCategories";
    static dependencies = ["megaMenuOptionPlugin", "customizeWebsite"];
    async load({ editingElement }) {
        const module = this.dependencies.megaMenuOptionPlugin.getTemplatePrefix(
            editingElement,
            true
        );
        const cls = [...editingElement.firstElementChild.classList].find((cls) =>
            cls.startsWith("s_mega_menu_")
        );
        const templateKey = `${module}${cls}`;
        await this.dependencies.customizeWebsite.loadTemplateKey(templateKey);
        return templateKey;
    }
    apply({ editingElement, loadResult }) {
        this.dependencies.customizeWebsite.toggleTemplate(
            {
                editingElement,
                params: { view: loadResult },
            },
            true
        );
    }
}

registry
    .category("website-plugins")
    .add(WebsiteSaleMegaMenuOptionPlugin.id, WebsiteSaleMegaMenuOptionPlugin);
