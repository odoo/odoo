/** @odoo-module **/

import core from "web.core";
import Dialog from "web.Dialog";

var _t = core._t;

const ColorpickerDialog = Dialog.extend({
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
        this.colorPicker = new ColorpickerWidget(this, Object.assign({
            colorPreview: true,
        }, this.options));
        proms.push(this.colorPicker.appendTo(this.$el));
        return Promise.all(proms);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onFinalPick: function () {
        this.trigger_up('colorpicker:saved', this.colorPicker.colorComponents);
    },
});

export default {
    ColorpickerDialog: ColorpickerDialog,
};
