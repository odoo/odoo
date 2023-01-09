odoo.define('survey.timer', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.SurveyTimerWidget = publicWidget.Widget.extend({
    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.timer = params.timer;
        this.timeLimitMinutes = params.timeLimitMinutes;
        this.surveyTimerInterval = null;
        this.timeDifference = null;
        if (params.serverTime) {
            this.timeDifference = moment.utc().diff(moment.utc(params.serverTime), 'milliseconds');
        }
    },


    /**
    * Two responsabilities : Validate that time limit is not exceeded and Run timer otherwise.
    * If end-user's clock OR the system clock  is de-synchronized before the survey is started, we apply the
    * difference in timer (if time difference is more than 5 seconds) so that we can
    * display the 'absolute' counter
    *
    * @override
    */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.countDownDate = moment.utc(self.timer).add(self.timeLimitMinutes, 'minutes');
            if (Math.abs(self.timeDifference) >= 5000) {
                self.countDownDate = self.countDownDate.add(self.timeDifference, 'milliseconds');
            }
            if (self.timeLimitMinutes <= 0 || self.countDownDate.diff(moment.utc(), 'seconds') < 0) {
                self.trigger_up('time_up');
            } else {
                self._updateTimer();
                self.surveyTimerInterval = setInterval(self._updateTimer.bind(self), 1000);
            }
        });
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    _formatTime: function (time) {
        return time > 9 ? time : '0' + time;
    },

    /**
    * This function is responsible for the visual update of the timer DOM every second.
    * When the time runs out, it triggers a 'time_up' event to notify the parent widget.
    *
    * We use a diff in millis and not a second, that we round to the nearest second.
    * Indeed, a difference of 999 millis is interpreted as 0 second by moment, which is problematic
    * for our use case.
    */
    _updateTimer: function () {
        var timeLeft = Math.round(this.countDownDate.diff(moment.utc(), 'milliseconds') / 1000);

        if (timeLeft >= 0) {
            var timeLeftMinutes = parseInt(timeLeft / 60);
            var timeLeftSeconds = timeLeft - (timeLeftMinutes * 60);
            this.$el.text(this._formatTime(timeLeftMinutes) + ':' + this._formatTime(timeLeftSeconds));
        } else {
            clearInterval(this.surveyTimerInterval);
            this.trigger_up('time_up');
        }
    },
});

return publicWidget.registry.SurveyTimerWidget;

});
