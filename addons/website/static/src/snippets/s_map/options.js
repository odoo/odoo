odoo.define('options.s_map_options', function (require) {
'use strict';

const {_t} = require('web.core');
const options = require('web_editor.snippets.options');

options.registry.Map = options.Class.extend({
    /**
     *
     * @override
     */
    onBuilt: function () {
        this.updateUI();
    },

    /**
     * @override
     */
    updateUI() {
        const dataset = this.$target[0].dataset;
        const embedded = this.$target.find('.o_embedded');
        const info = this.$target.find('.missing_option_warning');
        if (dataset.mapAddress) {
            const url = 'https://maps.google.com/maps?q=' + encodeURIComponent(dataset.mapAddress)
                + '&t=' + encodeURIComponent(dataset.mapType)
                + '&z=' + encodeURIComponent(dataset.mapZoom)
                + '&ie=UTF8&iwloc=&output=embed';
            if (url !== embedded.attr('src')) {
                embedded.attr('src', url);
            }
            embedded.removeClass('d-none');
            info.addClass('d-none');
        } else {
            embedded.attr('src', 'about:blank');
            embedded.addClass('d-none');
            info.removeClass('d-none');
        }
        if (! (this.$target.hasClass('o_half_screen_height') || this.$target.hasClass('o_full_screen_height'))) {
            this.$target.css('min-height', this.$target[0].dataset.mapMinHeight);
        }
        return this._super.apply(this, arguments).then(() => {
            this.updateUIVisibility();
        });
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    async showDescription(previewMode, widgetValue, params) {
        const descriptionEl = this.$target[0].querySelector('.description');
        if (widgetValue && !descriptionEl) {
            this.$target.append($(`
                <div class="description">
                    <font>${_t('Visit us:')}</font>
                    <span>${_t('Our office is open Monday – Friday 8:30 a.m. – 4:00 p.m.')}</span>
                </div>`)
            );
        } else if (!widgetValue && descriptionEl) {
            descriptionEl.remove();
        }
    },
    /**
     * @see this.selectClass for parameters
     */
    async setHeight(previewMode, widgetValue, params) {
        if (widgetValue) {
            this.$target[0].dataset.mapMinHeight = widgetValue;
            this.$target.css('min-height', widgetValue);
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
            return !!this.$target[0].querySelector('.description');
        }
        if (methodName === 'setHeight') {
            return this.$target[0].dataset.mapMinHeight;
        }
        return this._super(...arguments);
    },
});
});
