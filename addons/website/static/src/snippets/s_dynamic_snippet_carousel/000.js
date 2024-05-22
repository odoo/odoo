odoo.define('website.s_dynamic_snippet_carousel', function (require) {
'use strict';

const config = require('web.config');
const core = require('web.core');
const publicWidget = require('web.public.widget');
const DynamicSnippet = require('website.s_dynamic_snippet');

const DynamicSnippetCarousel = DynamicSnippet.extend({
    selector: '.s_dynamic_snippet_carousel',
    xmlDependencies: (DynamicSnippet.prototype.xmlDependencies || []).concat(
        ['/website/static/src/snippets/s_dynamic_snippet_carousel/000.xml']
    ),

    /**
     *
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
                interval: parseInt(this.$target[0].dataset.carouselInterval),
            },
        );
    },
    /**
     * @deprecated
     * @todo remove me in master, this was wrongly named and was supposed to
     * override _getQWebRenderOptions. This is kept for potential custo in
     * stable, although note that without hacks, calling this._super here just
     * crashes.
     */
    _getQWebRenderParams: function () {
        return Object.assign(
            this._super.apply(this, arguments),
            {
                interval: parseInt(this.$target[0].dataset.carouselInterval),
            },
        );
    },
});
publicWidget.registry.dynamic_snippet_carousel = DynamicSnippetCarousel;

return DynamicSnippetCarousel;
});
