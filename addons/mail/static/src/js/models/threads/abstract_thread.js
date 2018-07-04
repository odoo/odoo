odoo.define('mail.model.AbstractThread', function (require) {
"use strict";

var Class = require('web.Class');

/**
 * Abstract thread is the super class of all threads, either backend threads
 * (which are compatible with mail service) or website livechats.
 */
var AbstractThread = Class.extend({
    init: function (parent, data) {},

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    getMessages: function () {},
});

return AbstractThread;

});
