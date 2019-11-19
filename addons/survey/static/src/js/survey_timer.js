odoo.define('survey.timer', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

var interval = null;
var $timer = null;
var countDownDate = null;

publicWidget.registry.SurveyTimerWidget = publicWidget.Widget.extend({
    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.$timer = params.timer;
        this.$timeLimitMinutes = params.timeLimitMinutes;
    },


    /**
    * Two responsabilities : Validate that time limit is not exceeded and Run timer otherwise.
    *
    * @override
    */
    start: function () {
        var superDef = this._super.apply(this, arguments);

        countDownDate = moment.utc(this.$timer).add(this.$timeLimitMinutes, 'minutes');
        if (this.$timeLimitMinutes <= 0 || countDownDate.diff(moment.utc(), 'seconds') < 0) {
            this.trigger_up('time_up');
        } else {
            $timer = this.$el.find('.timer');
            this._updateTimer(this);
            interval = setInterval(this._updateTimer.bind(this), 1000);
        }

        return superDef;
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
    */
    _updateTimer: function () {
        var timeLeft = countDownDate.diff(moment.utc(), 'seconds');

        if (timeLeft >= 0) {
            var timeLeftMinutes = parseInt(timeLeft / 60);
            var timeLeftSeconds = timeLeft - (timeLeftMinutes * 60);
            $timer.html(this._formatTime(timeLeftMinutes) + ':' + this._formatTime(timeLeftSeconds));
        } else {
            clearInterval(interval);
            this.trigger_up('time_up');
        }
    },
});

return publicWidget.registry.SurveyTimerWidget;

});
