odoo.define('survey.session_manage_test', function (require) {
"use strict";

var SessionManager = require('survey.session_manage');
/**
 * Small override for test/tour purposes.
 * We trigger the fetch of answer results immediately at the start.
 * (Instead of wasting 2 seconds waiting after the start).
 */
SessionManager.include({
    start: function () {
        return this._super.apply(this, arguments)
            .then(this._refreshResults.bind(this));
    }
});

return SessionManager;

});
