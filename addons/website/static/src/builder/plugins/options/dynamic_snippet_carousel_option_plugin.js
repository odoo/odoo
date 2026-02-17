import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { setDatasetIfUndefined } from "./dynamic_snippet_option_plugin";
import { BuilderAction } from "@html_builder/core/builder_action";

/**
 * @typedef { Object } DynamicSnippetCarouselOptionShared
 * @property { DynamicSnippetCarouselOptionPlugin['setOptionsDefaultValues'] } setOptionsDefaultValues
 * @property { DynamicSnippetCarouselOptionPlugin['updateTemplateSnippetCarousel'] } updateTemplateSnippetCarousel
 * @property { DynamicSnippetCarouselOptionPlugin['getModelNameFilter'] } getModelNameFilter
 */

export class DynamicSnippetCarouselOptionPlugin extends Plugin {
    static id = "dynamicSnippetCarouselOption";
    static shared = [
        "setOptionsDefaultValues",
        "updateTemplateSnippetCarousel",
        "getModelNameFilter",
    ];
    static dependencies = ["dynamicSnippetOption"];
    modelNameFilter = "";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetCarouselSliderSpeedAction,
        },
        dynamic_snippet_template_updated: this.onTemplateUpdated.bind(this),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    onTemplateUpdated({ el, template }) {
        if (el.matches(".s_dynamic_snippet_carousel")) {
            this.updateTemplateSnippetCarousel(el, template);
        }
    }
    updateTemplateSnippetCarousel(el, template) {
        if (template.rowPerSlide) {
            el.dataset.rowPerSlide = template.rowPerSlide;
        } else {
            delete el.dataset.rowPerSlide;
        }
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_dynamic_snippet_carousel")) {
            await this.setOptionsDefaultValues(snippetEl, this.modelNameFilter);
        }
    }
    async setOptionsDefaultValues(snippetEl, modelNameFilter, contextualFilterDomain = []) {
        await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
            snippetEl,
            modelNameFilter,
            contextualFilterDomain
        );
        setDatasetIfUndefined(snippetEl, "carouselInterval", "5000");
    }
}

export class SetCarouselSliderSpeedAction extends BuilderAction {
    static id = "setCarouselSliderSpeed";
    apply({ editingElement, value }) {
        editingElement.dataset.carouselInterval = value * 1000;
    }
    getValue({ editingElement }) {
        return editingElement.dataset.carouselInterval === undefined
            ? undefined
            : editingElement.dataset.carouselInterval / 1000;
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetCarouselOptionPlugin.id, DynamicSnippetCarouselOptionPlugin);
