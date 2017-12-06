odoo.define('web.RainbowEffect', function (require) {
"use strict";

var AbstractWebClient = require('web.AbstractWebClient');

AbstractWebClient.include({
    /**
     * Activate RainbowMan feature
     * @override
     */
    init: function() {
        this._super.apply(this, arguments);
        this.show_rainbowman = true;
    },
});

});
