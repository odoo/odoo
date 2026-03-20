import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class DisplayTimer extends Interaction {
    static selector = ".o_display_timer";
    dynamicContent = {
        "span.o_timer_days": { "t-out": () => this.daysText },
        "span.o_timer_hours": { "t-out": () => this.hoursText },
        "span.o_timer_minutes": { "t-out": () => this.minutesText },
        "span.o_timer_seconds": { "t-out": () => this.secondsText },
    };

    /**
     * This interaction allows to display a DOM element at the end of a certain time laps.
     * There are 2 timers available:
     *   - The main-timer: display the DOM element (using the displayClass) at the end of this timer.
     *   - The pre-timer: additional timer to display the main-timer. This pre-timer can be invisible or visible,
     *                    depending of the startCountdownDisplay option. Once the pre-timer is over,
     *                    the main-timer is displayed.
     */
    setup() {
        const options = this.el.dataset;

        this.preCountdownTime = parseInt(options["preCountdownTime"]);
        this.mainCountdownTime = parseInt(options["mainCountdownTime"]);
        this.mainCountdownText = options["mainCountdownText"];
        this.hasMainTimeDisplay = options["mainCountdownDisplay"] === "true";

        this.displayClass = options["displayClass"];

        if (options["preCountdownDisplay"] === "true") {
            this.el.parentElement.classList.remove("d-none");
        }

        this.checkTimer();
        this.interval = setInterval(() => { this.checkTimer(); }, 1000);
        this.registerCleanup(() => clearInterval(this.interval));
    }

    /**
     * This method removes 1 second to the current timer (pre-timer or
     * main-timer) and calls the method to update the DOM, unless main-timer is
     * over. In that last case, the DOM element to show is displayed.
     */
    checkTimer() {
        const now = new Date();

        const remainingPreSeconds = this.preCountdownTime - (now.getTime() / 1000);
        if (remainingPreSeconds <= 1) {
            const countdownTextEl = this.el.querySelector(".o_countdown_text");
            if (countdownTextEl) {
                countdownTextEl.textContent = this.mainCountdownText;
            }
            if (this.hasMainTimeDisplay) {
                this.el.parentElement.classList.remove("d-none");
            }
            const remainingMainSeconds = this.mainCountdownTime - (now.getTime() / 1000);
            if (remainingMainSeconds <= 1) {
                clearInterval(this.interval);
                document.querySelector(this.displayClass).classList.remove("d-none");
                this.el.parentElement.classList.add("d-none");
            } else {
                this.updateCountdown(remainingMainSeconds);
            }
        } else {
            this.updateCountdown(remainingPreSeconds);
        }
    };

    /**
     * This method update the DOM to display the remaining time.
     * from seconds, the method extract the number of days, hours, minutes and seconds and
     * override the different DOM elements values.
     *
     * @param {number} remainingTime
     */
    updateCountdown(remainingTime) {
        let remainingSeconds = remainingTime;
        this.daysText = Math.floor(remainingSeconds / 86400).toString();

        remainingSeconds = remainingSeconds % 86400;
        this.hoursText = this.formatTime(Math.floor(remainingSeconds / 3600));

        remainingSeconds = remainingSeconds % 3600;
        this.minutesText = this.formatTime(Math.floor(remainingSeconds / 60));

        this.secondsText = this.formatTime(Math.floor(remainingSeconds % 60));
    }

    /**
     * Format the number to a 2 char strings
     * 
     * @param {number} num
     */
    formatTime(num) {
        return (num < 10 ? "0" : "") + num;
    }
}

registry
    .category("public.interactions")
    .add("website_event.display_timer", DisplayTimer);
