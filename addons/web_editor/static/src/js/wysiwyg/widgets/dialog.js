odoo.define('wysiwyg.widgets.Dialog', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');

var _t = core._t;

/**
 * Extend Dialog class to handle save/cancel of edition components.
 */
var SummernoteDialog = Dialog.extend({
    /**
     * @constructor
     */
    init: function (parent, options) {
        this.options = options || {};
        this._super(parent, _.extend({}, {
            buttons: [{
                    text: this.options.save_text || _t("Save"),
                    classes: 'btn-primary',
                    click: this.save,
                },
                {
                    text: _t("Discard"),
                    close: true,
                }
            ]
        }, this.options));

        this.destroyAction = 'cancel';

        var self = this;
        this.opened(function () {
            self.$('input:first').focus();
            self.$el.closest('.modal').on('hidden.bs.modal', self.options.onClose);
        });
        this.on('closed', this, function () {
            this.trigger(this.destroyAction, this.final_data || null);
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Called when the dialog is saved. Set the destroy action type to "save"
     * and should set the final_data variable correctly before closing.
     */
    save: function () {
        this.destroyAction = "save";
        this.close();
    },
});

return SummernoteDialog;
});
