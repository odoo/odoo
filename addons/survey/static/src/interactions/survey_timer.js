import { Interaction } from "@web/public/interaction";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
const { DateTime } = luxon;

export class SurveyTimer extends Interaction {
    static selector = ".o_survey_timer_container .o_survey_timer";

    setup() {
        const timerDataEl = document.querySelector(".o_survey_form_content_data");
        this.timeLimitMinutes = Number(timerDataEl.dataset.timeLimitMinutes);
        this.timer = timerDataEl.dataset.timer;
        this.timeDifference = null;
        this.surveyTimerInterval = null;
        const serverTime = timerDataEl.dataset.serverTime;
        if (serverTime) {
            this.timeDifference = DateTime.utc().diff(
                deserializeDateTime(serverTime)
            ).milliseconds;
        }
        this.setupTimer();
    }

    /**
    * Two responsibilities: Validate that the time limit is not exceeded and Run timer otherwise.
    * If the end-user's clock OR the system clock is desynchronized,
    * we apply the difference in the clocks (if the time difference is more than 500 ms).
    * This makes the timer fair across users and helps avoid early submissions to the server.
    */
    setupTimer() {
        this.countDownDate = DateTime.fromISO(this.timer, { zone: "utc" }).plus({
            minutes: this.timeLimitMinutes,
        });
        if (Math.abs(this.timeDifference) >= 500) {
            this.countDownDate = this.countDownDate.plus({ milliseconds: this.timeDifference });
        }
        if (this.timeLimitMinutes <= 0 || this.countDownDate.diff(DateTime.utc()).seconds < 0) {
            this.triggerTimeUp();
        } else {
            this.updateTimer();
            this.surveyTimerInterval = setInterval(this.updateTimer.bind(this), 1000);
        }
    }

    formatTime(time) {
        return time > 9 ? time : "0" + time;
    }

    triggerTimeUp() {
        this.el.dispatchEvent(new Event("time_up"));
    }

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
            this.el.textContent =
                this.formatTime(timeLeftMinutes) + ":" + this.formatTime(timeLeftSeconds);
        } else {
            if (this.surveyTimerInterval) {
                clearInterval(this.surveyTimerInterval);
            }
            this.triggerTimeUp();
        }
    }
}

registry.category("public.interactions").add("survey.SurveyTimer", SurveyTimer);
