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
    }

});

options.registry.dynamic_snippet_carousel = dynamicSnippetCarouselOptions;

return dynamicSnippetCarouselOptions;
});
