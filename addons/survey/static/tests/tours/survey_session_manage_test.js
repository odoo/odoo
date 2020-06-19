odoo.define('survey.session_manage_test', function (require) {
"use strict";

var SessionManager = require('survey.session_manage');
/**
 * Small override for test/tour purposes.
 */
SessionManager.include({
    /**
     * - Trigger the fetch of answer results immediately at the start.
     * (Instead of wasting 2 seconds waiting after the start).
     * - Set the fade in/out time to 1 ms to avoid unnecessary delays.
     * - Avoid refreshing the results every 2 seconds
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments)
            .then(this._refreshResults.bind(this))
            .then(function () {
                self.fadeInOutTime = 1;
                clearInterval(self.resultsRefreshInterval);
            });
    },

    /**
     * Force the timer to "now" to avoid introducing potential test breaking
     * timely variables (rpc/small server delay/...) if the start_question_time flickers.
     */
    _startTimer: function () {
        this.$el.data('timer', moment.utc());
        return this._super.apply(this, arguments);
    }
});

return SessionManager;

});
