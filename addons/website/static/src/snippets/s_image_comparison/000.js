/** @odoo-module */

import publicWidget from 'web.public.widget';
import {qweb} from 'web.core';

const ImageComparisonWidget = publicWidget.Widget.extend({
    selector: '.s_image_comparison',
    xmlDependencies: ['/website/static/src/snippets/s_image_comparison/000.xml'],
    disabledInEditableMode: false,
    events: {
        'input input[type="range"]': '_onSliderInput',
    },
    read_events: {
        'click figure': '_onFigureClick',
        'click .o_enlarge_button': '_onEnlargeButtonClick',
    },

    /**
     * @override
     */
    destroy() {
        const slideValue = 50;
        this.$target[0].querySelector('input[type="range"]').value = slideValue;
        this._slideImage(slideValue);
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onEnlargeButtonClick(ev) {
        if (this.$modal) {
            return;
        }
        const imageEls = this.$target[0].querySelectorAll('.o_media_right, .o_media_left');
        const descriptions = Array.from(this.$target[0].querySelectorAll('.o_description'))
            .map(el => el.innerText);
        this.$modal = $(qweb.render('website.image.comparison.modal', {
            images: Array.from(imageEls),
            descriptions,
        }));
        this.$modal.one('shown.bs.modal', () => {
            this.trigger_up('widgets_start_request', {
                editableMode: false,
                $target: this.$modal.find('.s_image_comparison'),
            });
        });
        this.$modal.on('hidden.bs.modal', () => {
            this.$modal = undefined;
        });

        const modalBS = new Modal(this.$modal[0], {keyboard: true, backdrop: true});
        modalBS.show();
        ev.stopPropagation();
    },
    /**
     * @private
     * @param  {Event} ev
     */
    _onFigureClick(ev) {
        // When the user clicks on an image the slider has to move to the place
        // where he clicked. We have to do this manually because only the
        // pointer events of the thumb part of the input range are activated
        // (to allow the tooltips to work, activation of the image options, ...)
        if (ev.target.matches('input')) {
            return;
        }
        const figurePosition = this.$target[0].querySelector('figure').getBoundingClientRect();
        const slideValue = 100 *
            (ev.clientX - figurePosition.left) / (figurePosition.right - figurePosition.left);
        this.$target[0].querySelector('input[type="range"]').value = slideValue;
        this._slideImage(slideValue);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onSliderInput(ev) {
        // In edit mode, do not consider the slide as a history step.
        if (this.editableMode) {
            this.options.wysiwyg.odooEditor.observerUnactive();
        }
        const slideValue = this.$target[0].querySelector('input[type="range"]').value;
        this._slideImage(slideValue);
        if (this.editableMode) {
            this.options.wysiwyg.odooEditor.observerActive();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adapts the image according to the value of the slider
     *
     * @private
     * @param  {Number} slideValue
     */
    _slideImage(slideValue) {
        this.$target[0].querySelector('.o_media_left').style.clipPath =
            `polygon(0 0, ${slideValue}% 0, ${slideValue}% 100%, 0 100%)`;
    },
});
publicWidget.registry.s_image_comparison = ImageComparisonWidget;
export default ImageComparisonWidget;
