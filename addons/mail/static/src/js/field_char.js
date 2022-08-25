/** @odoo-module **/

import { debounce } from "@web/core/utils/timing";
import { FieldChar } from 'web.basic_fields';

FieldChar.include({

    //--------------------------------------------------------------------------
    // Public
    //-------------------------------------------------------------------------

    /**
     * Support a key-based onchange in text field.
     * The _triggerOnchange method is debounced to run after given debouce delay
     * (or 2 seconds by default) on typing ends.
     *
     */
    init: function () {
        this._super.apply(this, arguments);
        if (this.nodeOptions.keydown_debounce_delay === undefined) {
            this.nodeOptions.keydown_debounce_delay = 2000;
        }
        this._triggerOnchange = debounce(this._triggerOnchange, this.nodeOptions.keydown_debounce_delay);
    },


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Trigger the 'change' event at key down. It allows to trigger an onchange
     * while typing which may be interesting in some cases. Otherwise onchange
     * is triggered only on blur.
     *
     * @override
     * @private
     */
    _onKeydown: function () {
        this._super.apply(this, arguments);
        if (this.nodeOptions.onchange_on_keydown) {
            this._triggerOnchange();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Triggers the 'change' event to refresh the value.
     * This method is debounced to run after given debouce delay on typing ends.
     * (to avoid spamming the server while the user is typing their message)
     *
     * @private
     */
    _triggerOnchange: function () {
        this.$input.trigger('change');
    },
});
