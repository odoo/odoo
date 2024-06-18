/** @odoo-module **/

import { DynamicSnippetOptions } from "@website/snippets/s_dynamic_snippet/options";
import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";

export class DynamicSnippetCarouselOptions extends DynamicSnippetOptions {

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     *
     * @override
     * @private
     */
    _setOptionsDefaultValues() {
        super._setOptionsDefaultValues(this, arguments);
        this._setOptionValue('carouselInterval', '5000');
    }
    /**
     * Take the new template selection into account
     *
     * @param {number} newTemplate id of the newly selected template
     * @param {number} oldTemplate id of the previously selected template
     * @override
     */
    _templateUpdated(newTemplate, oldTemplate) {
        super._templateUpdated(...arguments);
        const template = this.dynamicFilterTemplates[newTemplate];
        if (template.rowPerSlide) {
            this.$target[0].dataset.rowPerSlide = template.rowPerSlide;
        } else {
            delete this.$target[0].dataset.rowPerSlide;
        }
        if (template.arrowPosition) {
            this.$target[0].dataset.arrowPosition = template.arrowPosition;
        } else {
            delete this.$target[0].dataset.arrowPosition;
        }
    }

}

registerWebsiteOption("DynamicSnippetCarouselOptions", {
    Class: DynamicSnippetCarouselOptions,
    template: "website.s_dynamic_snippet_carousel_option",
    selector: "[data-snippet='s_dynamic_snippet_carousel']",
});
