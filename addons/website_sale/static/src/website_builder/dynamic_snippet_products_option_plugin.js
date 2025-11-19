import { BuilderAction } from "@html_builder/core/builder_action";
import { DYNAMIC_SNIPPET_CAROUSEL } from "@website/builder/plugins/options/dynamic_snippet_carousel_option_plugin";
import { setDatasetIfUndefined } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import {
    DynamicSnippetProductsOption,
    getContextualFilterDomain,
} from "./dynamic_snippet_products_option";

class DynamicSnippetProductsOptionPlugin extends Plugin {
    static id = "dynamicSnippetProductsOption";
    static dependencies = ["dynamicSnippetCarouselOption"];
    static shared = ["fetchCategories", "getModelNameFilter"];
    modelNameFilter = "product.product";
    resources = {
        builder_options: withSequence(DYNAMIC_SNIPPET_CAROUSEL, DynamicSnippetProductsOption),
        dynamic_snippet_template_updated: this.onTemplateUpdated.bind(this),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        builder_actions: { GridColumnsAction, MobileColumnsAction }
    };
    setup() {
        this.categories = undefined;
    }
    destroy() {
        super.destroy();
        this.categories = undefined;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(DynamicSnippetProductsOption.selector)) {
            for (const [optionName, value] of [
                ["productCategoryId", "all"],
                ["setOrientation", "carousel"],
                ["showVariants", true],
                ["numberOfRecords", 2]
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
        if (el.matches(DynamicSnippetProductsOption.selector)) {
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

export class GridColumnsAction extends BuilderAction {
    static id = "gridColumns";

    isApplied({ editingElement, value }) {
        return parseInt(editingElement.dataset.gridColumns) === value;
    }
    getValue({ editingElement }) {
        return parseInt(editingElement.dataset.gridColumns);
    }
    apply({ editingElement, value }) {
        editingElement.dataset.gridColumns = value;
    }
}

export class MobileColumnsAction extends BuilderAction {
    static id = "mobileColumns";

    isApplied({ editingElement, value }) {
        return parseInt(editingElement.dataset.mobileColumns) === value;
    }
    getValue({ editingElement }) {
        return parseInt(editingElement.dataset.mobileColumns);
    }
    apply({ editingElement, value }) {
        editingElement.dataset.mobileColumns = value;
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetProductsOptionPlugin.id, DynamicSnippetProductsOptionPlugin);
