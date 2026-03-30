import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { getContextualFilterDomain } from "./dynamic_snippet_products_option";

export class DynamicSnippetProductsOptionPlugin extends Plugin {
    static id = "dynamicSnippetProductsOption";
    static shared = ["fetchCategories"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dynamic_filter_contextual_domain_processors: (domain, { snippetEl }) => {
            if (snippetEl.matches(".s_dynamic_snippet_products")) {
                domain.push(...getContextualFilterDomain(this.editable));
            }
            return domain;
        },
        model_name_filter_overrides: (snippetEl) => {
            if (snippetEl.matches(".s_dynamic_snippet_products")) {
                return "product.product";
            }
        },
    };
    setup() {
        this.categories = undefined;
    }
    destroy() {
        super.destroy();
        this.categories = undefined;
    }
    async fetchCategories() {
        if (!this.categories) {
            this.categories = this._fetchCategories();
        }
        return this.categories;
    }
    async _fetchCategories() {
        // TODO put in an utility function
        const websiteDomain = [
            "|",
            ["website_id", "=", false],
            ["website_id", "=", this.services.website.currentWebsite.id],
        ];
        return this.services.orm.searchRead(
            "product.public.category",
            websiteDomain,
            ["id", "name"],
            { order: "name asc" }
        );
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetProductsOptionPlugin.id, DynamicSnippetProductsOptionPlugin);
