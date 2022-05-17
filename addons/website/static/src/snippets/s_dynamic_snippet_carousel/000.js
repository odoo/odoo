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
     * @todo remove me in master.
     */
    _renderContent: function () {
        this._super.apply(this, arguments);
        this._computeHeights();
    },
    /**
     * @todo remove me in master. This is already automatically done by the
     * related public widget which is also in charge of initializing the
     * carousel behaviors. This is left to be done twice in stable to not break
     * potential custo.
     */
    _computeHeights: function () {
        var maxHeight = 0;
        var $items = this.$('.carousel-item');
        $items.css('min-height', '');
        _.each($items, function (el) {
            var $item = $(el);
            var isActive = $item.hasClass('active');
            $item.addClass('active');
            var height = $item.outerHeight();
            if (height > maxHeight) {
                maxHeight = height;
            }
            $item.toggleClass('active', isActive);
        });
        $items.css('min-height', maxHeight);
    },
});
publicWidget.registry.dynamic_snippet_carousel = DynamicSnippetCarousel;

return DynamicSnippetCarousel;
});
