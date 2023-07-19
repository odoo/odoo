/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ComponentWrapper } from "web.OwlCompatibility";

import Dialog from "web.Dialog";
import { Colorpicker } from '@web/core/colorpicker/colorpicker';

export const ColorpickerDialog = Dialog.extend({
    /**
     * @override
     */
    init: function (parent, options) {
        this.options = options || {};
        this._super(parent, Object.assign({
            size: 'small',
            title: _t('Pick a color'),
            buttons: [
                {text: _t('Choose'), classes: 'btn-primary', close: true, click: this._onFinalPick.bind(this)},
                {text: _t('Discard'), close: true},
            ],
        }, this.options));
    },
    /**
     * @override
     */
    start: function () {
        const proms = [this._super(...arguments)];
        this.colorpicker = new ComponentWrapper(this, Colorpicker, {
            colorPreview: true,
        });
        this._colorpickerComponent = this.colorpicker.node.component;
        proms.push(this.colorpicker.mount(this.$el[0]));
        return Promise.all(proms);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onFinalPick: function () {
        this.trigger_up('colorpicker:saved', this._colorpickerComponent.colorComponents);
    },
});
