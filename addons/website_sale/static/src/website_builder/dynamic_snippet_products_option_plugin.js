import { setDatasetIfUndefined } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { getContextualFilterDomain } from "./dynamic_snippet_products_option";

export class DynamicSnippetProductsOptionPlugin extends Plugin {
    static id = "dynamicSnippetProductsOption";
    static dependencies = ["dynamicSnippetCarouselOption"];
    static shared = ["fetchCategories", "getModelNameFilter"];
    modelNameFilter = "product.product";
    resources = {
        dynamic_snippet_template_updated: this.onTemplateUpdated.bind(this),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };
    setup() {
        this.categories = undefined;
    }
    destroy() {
        super.destroy();
        this.categories = undefined;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_dynamic_snippet_products")) {
            for (const [optionName, value] of [
                ["productCategoryId", "all"],
                ["showVariants", true],
            ]) {
                setDatasetIfUndefined(snippetEl, optionName, value);
            }
            await this.dependencies.dynamicSnippetCarouselOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter,
                getContextualFilterDomain(this.editable)
            );
        }
    }
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    onTemplateUpdated({ el, template }) {
        if (el.matches(".s_dynamic_snippet_products")) {
            this.dependencies.dynamicSnippetCarouselOption.updateTemplateSnippetCarousel(
                el,
                template
            );
        }
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
