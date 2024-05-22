odoo.define('sms.onchange_in_keyup', function (require) {
"use strict";

var FieldChar = require('web.basic_fields').FieldChar;
FieldChar.include({

    //--------------------------------------------------------------------------
    // Public
    //-------------------------------------------------------------------------

    /**
     * Support a key-based onchange in text field. In order to avoid too much
     * rpc to the server _triggerOnchange is throttled (once every second max)
     *
     */
    init: function () {
        this._super.apply(this, arguments);
        this._triggerOnchange = _.throttle(this._triggerOnchange, 1000, {leading: false});
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
     * Triggers the 'change' event to refresh the value. Throttled at init to
     * avoid spaming server.
     *
     * @private
     */
    _triggerOnchange: function () {
        this.$input.trigger('change');
    },
});

});
