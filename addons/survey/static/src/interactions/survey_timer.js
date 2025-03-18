import { deserializeDateTime } from "@web/core/l10n/dates";
import publicWidget from "@web/legacy/js/public/public_widget";
const { DateTime } = luxon;

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
            this.timeDifference = DateTime.utc().diff(
                deserializeDateTime(params.serverTime)
            ).milliseconds;
        }
    },


    /**
    * Two responsibilities: Validate that the time limit is not exceeded and Run timer otherwise.
    * If the end-user's clock OR the system clock is desynchronized,
    * we apply the difference in the clocks (if the time difference is more than 500 ms).
    * This makes the timer fair across users and helps avoid early submissions to the server.
    *
    * @override
    */
    async start() {
        await this._super.apply(this, arguments);
        this.countDownDate = DateTime.fromISO(this.timer, { zone: "utc" }).plus({
            minutes: this.timeLimitMinutes,
        });
        if (Math.abs(this.timeDifference) >= 500) {
            this.countDownDate = this.countDownDate.plus({ milliseconds: this.timeDifference });
        }
        if (this.timeLimitMinutes <= 0 || this.countDownDate.diff(DateTime.utc()).seconds < 0) {
            this.trigger_up("time_up");
        } else {
            this.updateTimer();
            this.surveyTimerInterval = setInterval(this.updateTimer.bind(this), 1000);
        }
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    formatTime(time) {
        return time > 9 ? time : "0" + time;
    },

    /**
     * This function is responsible for the visual update of the timer DOM every second.
     * When the time runs out, it triggers a 'time_up' event to notify the parent widget.
     *
     * We use a diff in millis and not a second, that we round to the nearest second.
     * Indeed, a difference of 999 millis is interpreted as 0 second by moment, which is problematic
     * for our use case.
     */
    updateTimer() {
        const timeLeft = Math.round(this.countDownDate.diff(DateTime.utc()).milliseconds / 1000);

        if (timeLeft >= 0) {
            const timeLeftMinutes = parseInt(timeLeft / 60);
            const timeLeftSeconds = timeLeft - (timeLeftMinutes * 60);
            this.$el.text(this.formatTime(timeLeftMinutes) + ":" + this.formatTime(timeLeftSeconds));
        } else {
            if (this.surveyTimerInterval) {
                clearInterval(this.surveyTimerInterval);
            }
            this.trigger_up("time_up");
        }
    },
});

export default publicWidget.registry.SurveyTimerWidget;
