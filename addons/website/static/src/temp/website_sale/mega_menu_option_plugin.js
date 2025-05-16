import { MegaMenuOptionPlugin } from "@website/website_builder/plugins/options/mega_menu_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

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
        "builder-options",
        "customizeWebsite",
        "history",
        "megaMenuOptionPlugin",
    ];
    resources = {
        builder_actions: this.getActions(),
        dropzone_selector: {
            selector: ".o_mega_menu .nav > .nav-link",
            dropIn: ".o_mega_menu nav",
            dropNear: ".o_mega_menu .nav-link",
        },
    };

    getActions() {
        return {
            toggleFetchEcomCategories: {
                load: async ({ editingElement }) => {
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
                },
                apply: ({ editingElement, loadResult }) => {
                    this.dependencies.customizeWebsite.toggleTemplate(
                        {
                            editingElement,
                            params: { view: loadResult },
                        },
                        true
                    );
                },
            },
        };
    }
}
registry
    .category("website-plugins")
    .add(WebsiteSaleMegaMenuOptionPlugin.id, WebsiteSaleMegaMenuOptionPlugin);
