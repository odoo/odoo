import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import {
    setDatasetIfUndefined,
    SetSectionTitlePositionAction,
} from "./dynamic_snippet_option_plugin";
import { BuilderAction } from "@html_builder/core/builder_action";
import { SetContainerWidthAction } from "../content_width_option_plugin";
import {
    DEFAULT_NUMBER_OF_ELEMENTS,
    DEFAULT_NUMBER_OF_ELEMENTS_FOR_TITLE_LEFT,
} from "@website/utils/constants";

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
        on_dynamic_snippet_template_updated_handlers: this.onTemplateUpdated.bind(this),
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

patch(SetContainerWidthAction.prototype, {
    apply({ editingElement: el, params: { mainParam: className } }) {
        super.apply(...arguments);
        const dynamicCarouselEl = el.closest(".o_dynamic_snippet_carousel");
        if (!dynamicCarouselEl || !el.querySelector(".s_dynamic_snippet_title_aside")) {
            return;
        }
        dynamicCarouselEl.dataset.numberOfElements =
            className !== "container-fluid"
                ? DEFAULT_NUMBER_OF_ELEMENTS_FOR_TITLE_LEFT
                : DEFAULT_NUMBER_OF_ELEMENTS;
    },
});

patch(SetSectionTitlePositionAction.prototype, {
    apply({ editingElement: el, params: { mainParam: classNames } }) {
        super.apply(...arguments);
        const dynamicCarouselEl = el.closest(".o_dynamic_snippet_carousel");
        if (!dynamicCarouselEl || el.closest(".container-fluid")) {
            return;
        }
        dynamicCarouselEl.dataset.numberOfElements = classNames.includes(
            "s_dynamic_snippet_title_aside"
        )
            ? DEFAULT_NUMBER_OF_ELEMENTS_FOR_TITLE_LEFT
            : DEFAULT_NUMBER_OF_ELEMENTS;
    },
});

registry
    .category("website-plugins")
    .add(DynamicSnippetCarouselOptionPlugin.id, DynamicSnippetCarouselOptionPlugin);
