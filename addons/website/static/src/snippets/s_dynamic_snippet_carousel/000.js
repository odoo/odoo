/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import DynamicSnippet from "@website/snippets/s_dynamic_snippet/000";
import { utils as uiUtils } from "@web/core/ui/ui_service";

const DynamicSnippetCarousel = DynamicSnippet.extend({
    selector: '.s_dynamic_snippet_carousel',
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.template_key = 'website.s_dynamic_snippet.carousel';
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getQWebRenderOptions: function () {
        return Object.assign(
            this._super.apply(this, arguments),
            {
                interval: parseInt(this.el.dataset.carouselInterval),
                rowPerSlide: parseInt(uiUtils.isSmall() ? 1 : this.el.dataset.rowPerSlide || 1),
                arrowPosition: this.el.dataset.arrowPosition || '',
            },
        );
    },
});
publicWidget.registry.dynamic_snippet_carousel = DynamicSnippetCarousel;

export default DynamicSnippetCarousel;
