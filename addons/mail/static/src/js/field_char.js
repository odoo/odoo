/** @odoo-module **/

import { FieldChar } from 'web.basic_fields';

FieldChar.include({

    //--------------------------------------------------------------------------
    // Public
    //-------------------------------------------------------------------------

    /**
     * Support a key-based onchange in text field.
     * The _triggerOnchange method is debounced to run 2 seconds after typing ends.
     *
     */
    init: function () {
        this._super.apply(this, arguments);
        this._triggerOnchange = _.debounce(this._triggerOnchange, 2000);
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
     * This method is debounced to run 2 seconds after typing ends.
     * (to avoid spamming the server while the user is typing his message)
     *
     * @private
     */
    _triggerOnchange: function () {
        this.$input.trigger('change');
    },
});
