/** @odoo-module */
import Dialog from "web.Dialog";
import core from "web.core";

/**
 * An extension of Dialog Widget to render warnings.
 */
export const WarningDialog = Dialog.extend({
    template: 'web.LegacyWarningDialog',
    /**
     * @param {Object} error
     * @param {string} error.message    the message in Warning Dialog
     *
     * @constructor
     */
    init: function (parent, options, error) {
        options.size = options.size || "medium";
        this._super.apply(this, [parent, options]);
        this.message = error.message;
        core.bus.off('close_dialogs', this);
    },
    /**
     * Focuses the ok button.
     *
     * @override
     */
    open: function () {
        this._super({shouldFocusButtons: true});
    },
});
