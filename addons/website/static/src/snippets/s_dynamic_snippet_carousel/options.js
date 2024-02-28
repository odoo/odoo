odoo.define('website.s_dynamic_snippet_carousel_options', function (require) {
'use strict';

const options = require('web_editor.snippets.options');
const s_dynamic_snippet_options = require('website.s_dynamic_snippet_options');

const dynamicSnippetCarouselOptions = s_dynamic_snippet_options.extend({
    /**
     * @override
     */
    onBuilt() {
        this._super(...arguments);
        // TODO Remove in master.
        this.$target[0].dataset['snippet'] = 's_dynamic_snippet_carousel';
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     *
     * @override
     * @private
     */
    _setOptionsDefaultValues: function () {
        this._super.apply(this, arguments);
        this._setOptionValue('carouselInterval', '5000');
    },
    /**
     * Take the new template selection into account
     *
     * @param {number} newTemplate id of the newly selected template
     * @param {number} oldTemplate id of the previously selected template
     * @override
     */
    _templateUpdated(newTemplate, oldTemplate) {
        this._super(...arguments);
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
    },

});

options.registry.dynamic_snippet_carousel = dynamicSnippetCarouselOptions;

return dynamicSnippetCarouselOptions;
});
