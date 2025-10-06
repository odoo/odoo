import { DYNAMIC_SNIPPET_CAROUSEL } from "@website/builder/plugins/options/dynamic_snippet_carousel_option_plugin";
import { setDatasetIfUndefined } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import {
    DynamicSnippetProductsOption,
    getContextualFilterDomain,
} from "./dynamic_snippet_products_option";
import { patch } from "@web/core/utils/patch";
import { SetContainerWidthAction } from "@website/builder/plugins/content_width_option_plugin";
import { BuilderAction } from "@html_builder/core/builder_action";

class DynamicSnippetProductsOptionPlugin extends Plugin {
    static id = "dynamicSnippetProductsOption";
    static dependencies = ["dynamicSnippetCarouselOption"];
    static shared = ["fetchCategories", "getModelNameFilter"];
    modelNameFilter = "product.product";
    resources = {
        builder_options: withSequence(DYNAMIC_SNIPPET_CAROUSEL, DynamicSnippetProductsOption),
        builder_actions: {
            SectionTitlePositionAction,
        },
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
        if (snippetEl.matches(DynamicSnippetProductsOption.selector)) {
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

patch(SetContainerWidthAction.prototype, {
    apply({ editingElement, params: { mainParam: className } }) {
        super.apply(...arguments);
        if (!editingElement.closest(".s_dynamic_snippet_products")) {
            return;
        }
        const isContentWidthMax = className === "container-fluid";
        const titleAsideEl = editingElement.querySelector(".s_dynamic_snippet_title_aside");
        const parentEl = editingElement.parentElement;
        const updatedNumberOfElements = !isContentWidthMax && titleAsideEl ? "2" : "4";
        if (parentEl.dataset.numberOfElements !== updatedNumberOfElements) {
            parentEl.dataset.numberOfElements = updatedNumberOfElements;
        }
    },
});

export class SectionTitlePositionAction extends BuilderAction {
    static id = "sectionTitlePosition";
    apply({ editingElement: el, params: { mainParam: position } }) {
        // Adjust dataset if title is aside and content-width is not max.
        if (el.closest(".container-fluid")) {
            return;
        }
        const productSnippetEl = el.closest(".s_dynamic_snippet_products");
        const updatedNumberOfElements = position === "left" ? "2" : "4";
        if (productSnippetEl.dataset.numberOfElements !== updatedNumberOfElements) {
            productSnippetEl.dataset.numberOfElements = updatedNumberOfElements;
        }
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetProductsOptionPlugin.id, DynamicSnippetProductsOptionPlugin);
