import { Plugin } from "@html_editor/plugin";
import { onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { DynamicSnippetCarouselOption } from "@html_builder/plugins/dynamic_snippet_carousel_option";

class DynamicSnippetProductsOptionPlugin extends Plugin {
    static id = "DynamicSnippetProductsOption";
    static dependencies = ["DynamicSnippetCarouselOption"];
    resources = {
        builder_options: {
            OptionComponent: DynamicSnippetProductsOption,
            props: {
                ...this.dependencies.DynamicSnippetCarouselOption.getComponentProps(),
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

export class DynamicSnippetProductsOption extends DynamicSnippetCarouselOption {
    static template = "website_sale.DynamicSnippetProductsOption";
    static components = { ...defaultBuilderComponents };
    static props = {
        ...DynamicSnippetCarouselOption.props,
        fetchCategories: Function,
    };
    setup() {
        super.setup();
        this.modelNameFilter = "product.product";
        this.saleState = useState({
            categories: [],
        });
        onWillStart(async () => {
            this.saleState.categories.push(...await this.props.fetchCategories());
        });
    }
}
