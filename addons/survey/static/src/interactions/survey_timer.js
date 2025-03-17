import { Interaction } from "@web/public/interaction";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
const { DateTime } = luxon;

class SurveyTimer extends Interaction {
    static selector = ".o_survey_timer_container .o_survey_timer";

    setup() {
        const timerDataEl = document.querySelector(".o_survey_form_content_data");
        this.timeLimitMinutes = Number(timerDataEl.dataset.timeLimitMinutes);
        this.timer = timerDataEl.dataset.timer;
        this.timeDifference = null;
        this.surveyTimerInterval = null;
        const serverTime = timerDataEl.dataset.serverTime;
        if (serverTime) {
            this.timeDifference = DateTime.utc().diff(deserializeDateTime(serverTime)).milliseconds;
        }

        this.countDownDate = DateTime.fromISO(this.timer, { zone: "utc" }).plus({
            minutes: this.timeLimitMinutes,
        });
        if (Math.abs(this.timeDifference) >= 5000) {
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

    updateTimer() {
        const timeLeft = Math.round(this.countDownDate.diff(DateTime.utc()).milliseconds / 1000);

        if (timeLeft >= 0) {
            const timeLeftMinutes = parseInt(timeLeft / 60);
            const timeLeftSeconds = timeLeft - timeLeftMinutes * 60;
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
