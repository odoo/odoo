import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.displayTimerWidget = publicWidget.Widget.extend({
    selector: '.o_display_timer',

    /**
     * This widget allows to display a dom element at the end of a certain time laps.
     * There are 2 timers available:
     *   - The main-timer: display the DOM element (using the displayClass) at the end of this timer.
     *   - The pre-timer: additional timer to display the main-timer. This pre-timer can be invisible or visible,
     *                    depending of the startCountdownDisplay option. Once the pre-timer is over,
                          the main-timer is displayed.
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.options = self.el.dataset;
            self.preCountdownDisplay = self.options["preCountdownDisplay"];
            self.preCountdownTime = parseInt(self.options["preCountdownTime"]);
            self.preCountdownText = self.options["preCountdownText"];

            self.mainCountdownTime = parseInt(self.options["mainCountdownTime"]);
            self.mainCountdownText = self.options["mainCountdownText"];
            self.mainCountdownDisplay = self.options["mainCountdownDisplay"];

            self.displayClass = self.options["displayClass"];

            if (self.preCountdownDisplay === "true") {
                self.el.parentElement.classList.remove("d-none");
            }

            self._checkTimer();
            self.interval = setInterval(function () { self._checkTimer(); }, 1000);
        });
    },

    /**
     * This method removes 1 second to the current timer (pre-timer or main-timer)
     * and call the method to update the DOM, unless main-timer is over. In that last case,
     * the DOM element to show is displayed.
     *
     * @private
     */
    _checkTimer: function () {
        var now = new Date();

        var remainingPreSeconds = this.preCountdownTime - (now.getTime()/1000);
        if (remainingPreSeconds <= 1) {
            this.el.querySelector(".o_countdown_text").textContent = this.mainCountdownText;
            if (this.mainCountdownDisplay === "true") {
                this.el.parentElement.classList.remove("d-none");
            }
            var remainingMainSeconds = this.mainCountdownTime - (now.getTime()/1000);
            if (remainingMainSeconds <= 1) {
                clearInterval(this.interval);
                document.querySelector(this.displayClass).classList.remove("d-none");
                this.el.parentElement.classList.add("d-none");
            } else {
                this._updateCountdown(remainingMainSeconds);
            }
        } else {
            this._updateCountdown(remainingPreSeconds);
        }
    },

    /**
     * This method update the DOM to display the remaining time.
     * from seconds, the method extract the number of days, hours, minutes and seconds and
     * override the different DOM elements values.
     *
     * @private
     */
    _updateCountdown: function (remainingTime) {
        var remainingSeconds = remainingTime;
        var days = Math.floor(remainingSeconds / 86400);

        remainingSeconds = remainingSeconds % 86400;
        var hours = Math.floor(remainingSeconds / 3600);

        remainingSeconds = remainingSeconds % 3600;
        var minutes = Math.floor(remainingSeconds / 60);

        remainingSeconds = Math.floor(remainingSeconds % 60);

        const daysEl = this.el.querySelector("span.o_timer_days");
        if (daysEl) {
            daysEl.textContent = days;
        }
        const hoursEl = this.el.querySelector("span.o_timer_hours");
        if (hoursEl) {
            hoursEl.textContent = this._zeroPad(hours, 2);
        }
        const minutesEl = this.el.querySelector("span.o_timer_minutes");
        if (minutesEl) {
            minutesEl.textContent = this._zeroPad(minutes, 2);
        }
        const secondsEl = this.el.querySelector("span.o_timer_seconds");
        if (secondsEl) {
            secondsEl.textContent = this._zeroPad(remainingSeconds, 2);
        }
    },

    /**
     * Small tool to add leading zéros to the given number, in function of the needed number of leading zéros.
     *
     * @private
     */
    _zeroPad: function (num, places) {
      var zero = places - num.toString().length + 1;
      return new Array(+(zero > 0 && zero)).join("0") + num;
    },

});

export default publicWidget.registry.countdownWidget;
