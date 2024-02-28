odoo.define('options.s_google_map_options', function (require) {
'use strict';

const {_t} = require('web.core');
const options = require('web_editor.snippets.options');

options.registry.GoogleMap = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    resetMapColor(previewMode, widgetValue, params) {
        this.$target[0].dataset.mapColor = '';
    },
    /**
     * @see this.selectClass for parameters
     */
    setFormattedAddress(previewMode, widgetValue, params) {
        this.$target[0].dataset.pinAddress = params.gmapPlace.formatted_address;
    },
    /**
     * @see this.selectClass for parameters
     */
    async showDescription(previewMode, widgetValue, params) {
        const descriptionEl = this.$target[0].querySelector('.description');
        if (widgetValue && !descriptionEl) {
            this.$target.append($(`
                <div class="description">
                    <font>${_t('Visit us:')}</font>
                    <span>${_t('Our office is located in the northeast of Brussels. TEL (555) 432 2365')}</span>
                </div>`)
            );
        } else if (!widgetValue && descriptionEl) {
            descriptionEl.remove();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'showDescription') {
            return this.$target[0].querySelector('.description') ? 'true' : '';
        }
        return this._super(...arguments);
    },
});
});
