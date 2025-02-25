import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { DynamicSnippetProductsOption } from "./dynamic_snippet_products_option";

class DynamicSnippetProductsOptionPlugin extends Plugin {
    static id = "dynamicSnippetProductsOption";
    static dependencies = ["dynamicSnippetCarouselOption"];
    resources = {
        builder_options: {
            OptionComponent: DynamicSnippetProductsOption,
            props: {
                ...this.dependencies.dynamicSnippetCarouselOption.getComponentProps(),
                fetchCategories: this.fetchCategories.bind(this),
            },
            selector: ".s_dynamic_snippet_products",
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
        const websiteDomain = ['|', ['website_id', '=', false], ['website_id', '=', this.services.website.currentWebsite.id]];
        return this.services.orm.searchRead("product.public.category", websiteDomain, ["id", "name"], { order: "name asc" });
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetProductsOptionPlugin.id, DynamicSnippetProductsOptionPlugin);

