import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { DynamicSnippetCarouselOption } from "./dynamic_snippet_carousel_option";
import { setDatasetIfUndefined } from "./dynamic_snippet_option_plugin";

class DynamicSnippetCarouselOptionPlugin extends Plugin {
    static id = "dynamicSnippetCarouselOption";
    static shared = ["setOptionsDefaultValues", "updateTemplateSnippetCarousel"];
    static dependencies = ["dynamicSnippetOption"];
    selector = ".s_dynamic_snippet_carousel";
    modelNameFilter = "";
    resources = {
        builder_actions: {
            setCarouselSliderSpeed: {
                apply: ({ editingElement, value }) => {
                    editingElement.dataset.carouselInterval = value * 1000;
                },
                getValue: ({ editingElement }) => editingElement.dataset.carouselInterval / 1000,
            },
        },
        builder_options: {
            OptionComponent: DynamicSnippetCarouselOption,
            props: {
                modelNameFilter: this.modelNameFilter,
            },
            selector: this.selector,
        },
        dynamic_snippet_template_updated: this.onTemplateUpdated.bind(this),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };
    onTemplateUpdated({ el, template }) {
        if (el.matches(this.selector)) {
            this.updateTemplateSnippetCarousel(el, template);
        }
    }
    updateTemplateSnippetCarousel(el, template) {
        if (template.rowPerSlide) {
            el.dataset.rowPerSlide = template.rowPerSlide;
        } else {
            delete el.dataset.rowPerSlide;
        }
        if (template.arrowPosition) {
            el.dataset.arrowPosition = template.arrowPosition;
        } else {
            delete el.dataset.arrowPosition;
        }
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(this.selector)) {
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

registry
    .category("website-plugins")
    .add(DynamicSnippetCarouselOptionPlugin.id, DynamicSnippetCarouselOptionPlugin);
