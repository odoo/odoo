odoo.define('website_event_track.website_event_lobby', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.websiteEventTrackTimer = publicWidget.Widget.extend({
    selector: '.o_wevent_track_countdown',

    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.countDownDate = moment.utc(self.$el.data('start'));
            self._updateTimer();
            self.surveyTimerInterval = setInterval(self._updateTimer.bind(self), 60000);
            return Promise.resolve();
        });
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    _formatTime: function (time) {
        return time > 9 ? time : '0' + time;
    },

    /**
    * This function is responsible for the visual update of the timer DOM every minute.
    *
    */
    _updateTimer: function () {
        var timeLeft = this.countDownDate.diff(moment.utc(), 'minutes');

        if (timeLeft >= 0) {
            var timeLeftHours = parseInt(timeLeft / 60);
            var timeLeftMinutes = timeLeft - (timeLeftHours * 60);
            this.$el.text(this._formatTime(timeLeftHours) + ':' + this._formatTime(timeLeftMinutes));
        } else {
            clearInterval(this.surveyTimerInterval);
        }
    }
});

return publicWidget.registry.websiteEventTrackTimer;

});
