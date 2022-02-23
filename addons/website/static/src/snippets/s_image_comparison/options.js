/** @odoo-module **/
import options from 'web_editor.snippets.options';
import {_t} from '@web/core/l10n/translation';

options.registry.ImageComparison = options.Class.extend({
    /**
     * @override
     */
    onBuilt() {
        for (const spanEl of this.$target[0]
            .querySelectorAll('.o_description > span, .o_media_right, .o_media_left')) {
            spanEl.setAttribute('contenteditable', 'true');
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Creates or removes the captions.
     *
     * @see this.selectClass for parameters
     */
    showCaptions(previewMode, widgetValue, params) {
        const descriptionEls = this.$target[0].querySelectorAll('.o_description');
        if (widgetValue && !descriptionEls.length) {
            // Create the two caption elements.
            const inputEl = this.$target[0].querySelector('input[type="range"]');
            for (const side of ['left', 'right']) {
                const divEl = document.createElement('div');
                divEl.className = `o_description o_${side}_description`;
                const spanEl = document.createElement('span');
                spanEl.setAttribute('contenteditable', 'true');
                spanEl.innerText = side === 'left' ? _t('BEFORE') : _t('AFTER');
                divEl.appendChild(spanEl);
                inputEl.after(divEl);
            }
        } else {
            for (const el of descriptionEls) {
                el.remove();
            }
        }
    },
    /**
     * Creates or removes the enlarge button.
     *
     * @see this.selectClass for parameters
     */
    showZoomButton(previewMode, widgetValue, params) {
        const buttonEl = this.$target[0].querySelector('.o_enlarge_button');
        if (widgetValue && !buttonEl) {
            const newButtonEl = document.createElement('button');
            newButtonEl.className = 'btn o_enlarge_button me-1 mb-1 o_not_customizable';
            newButtonEl.setAttribute('title', _t('Enlarge Images'));
            const iconEl = document.createElement('i');
            iconEl.className = 'fa fa-expand';
            newButtonEl.appendChild(iconEl);
            this.$target[0].querySelector('figure').appendChild(newButtonEl);
        } else {
            buttonEl.remove();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'showCaptions':
                return this.$target[0].querySelector('.o_description') ? 'true' : '';
            case 'showZoomButton':
                return this.$target[0].querySelector('.o_enlarge_button') ? 'true' : '';
        }
        return this._super(...arguments);
    },
});

options.registry.ImageComparisonImage = options.Class.extend({
    isTopOption: true,
    forceNoDeleteButton: true,

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        const currentSide = this.$target[0].classList.contains('o_media_right') ? 'right' : 'left';
        const leftPanelEl = this.$overlay.data('$optionsSection')[0];
        const titleTextEl = leftPanelEl.querySelector('we-title > span');
        titleTextEl.innerText = currentSide === 'right' ? _t('RIGHT Media') : _t('LEFT Media');

    },
});

export default {
    ImageComparisonImage: options.registry.ImageComparisonImage,
    ImageComparison: options.registry.ImageComparison,
};
