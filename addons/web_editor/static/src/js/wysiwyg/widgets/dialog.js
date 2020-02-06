odoo.define('wysiwyg.widgets.Dialog', function (require) {
'use strict';

var config = require('web.config');
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
        if (config.device.isMobile) {
            options.fullscreen = true;
        }
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
            self.$('input:visible:first').focus();
            self.$el.closest('.modal').addClass('o_web_editor_dialog');
            self.$el.closest('.modal').on('hidden.bs.modal', self.options.onClose);
        });
        this.on('closed', this, function () {
            self._toggleFullScreen();
            this.trigger(this.destroyAction, this.final_data || null);
        });
    },
    /**
     * Only use on config.device.isMobile, it's used by mass mailing to allow the dialog opening on fullscreen
     * @private
     */
    _toggleFullScreen: function() {
        if (config.device.isMobile && !this.hasFullScreen) {
            $('#iframe_target[isMobile="true"] #web_editor-top-edit .o_fullscreen').click();
        }
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
    /**
     * @override
     * @returns {*}
     */
    open: function() {
        this.hasFullScreen = $(window.top.document.body).hasClass('o_field_widgetTextHtml_fullscreen');
        this._toggleFullScreen();
        return this._super.apply(this, arguments);
    },
});

return SummernoteDialog;
});
