odoo.define('website.s_dynamic_snippet_carousel', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
const DynamicSnippet = require('website.s_dynamic_snippet');
const config = require('web.config');

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
                rowPerSlide: parseInt(config.device.isMobile ? 1 : this.el.dataset.rowPerSlide || 1),
                arrowPosition: this.el.dataset.arrowPosition || '',
            },
        );
    },
});
publicWidget.registry.dynamic_snippet_carousel = DynamicSnippetCarousel;

return DynamicSnippetCarousel;
});
