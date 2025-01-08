import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class DisplayTimer extends Interaction {
    static selector = ".o_display_timer";

    /**
     * This interaction allows to display a DOM element at the end of a certain time laps.
     * There are 2 timers available:
     *   - The main-timer: display the DOM element (using the displayClass) at the end of this timer.
     *   - The pre-timer: additional timer to display the main-timer. This pre-timer can be invisible or visible,
     *                    depending of the startCountdownDisplay option. Once the pre-timer is over,
                          the main-timer is displayed.
     */
    setup() {
        const options = this.el.dataset;
        this.preCountdownDisplay = options["preCountdownDisplay"];
        this.preCountdownTime = parseInt(options["preCountdownTime"]);
        this.preCountdownText = options["preCountdownText"];

        this.mainCountdownTime = parseInt(options["mainCountdownTime"]);
        this.mainCountdownText = options["mainCountdownText"];
        this.mainCountdownDisplay = options["mainCountdownDisplay"];

        this.displayClass = options["displayClass"];

        if (this.preCountdownDisplay === "true") {
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
            if (this.mainCountdownDisplay === "true") {
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
        const days = Math.floor(remainingSeconds / 86400);

        remainingSeconds = remainingSeconds % 86400;
        const hours = Math.floor(remainingSeconds / 3600);

        remainingSeconds = remainingSeconds % 3600;
        const minutes = Math.floor(remainingSeconds / 60);

        remainingSeconds = Math.floor(remainingSeconds % 60);

        const daysEl = this.el.querySelector("span.o_timer_days");
        if (daysEl) {
            daysEl.textContent = days.toString();
        }
        this.setTimeString("span.o_timer_hours", hours);
        this.setTimeString("span.o_timer_minutes", minutes);
        this.setTimeString("span.o_timer_seconds", remainingSeconds);
    }

    /**
     * @param {string} selector
     * @param {number} remainingNumber
     */
    setTimeString(selector, remainingNumber) {
        const el = this.el.querySelector(selector);
        if (el) {
            el.textContent = this.zeroPad(remainingNumber, 2);
        }
    }

    /**
     * Small tool to add leading zeros to the given number, according to the
     * needed number of leading zeros.
     *
     * @param {number} num
     * @param {number} places - number of characters wanted
     */
    zeroPad(num, places) {
      const zero = places - num.toString().length + 1;
      return new Array(+(zero > 0 && zero)).join("0") + num;
    }

}

registry.category("public.interactions").add("website_event.display_timer", DisplayTimer);
