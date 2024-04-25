/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.displayTimerWidget = publicWidget.Widget.extend({
    selector: '.o_display_timer',

    /**
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.options = self.el.dataset;
            self.preCountdownDisplay = self.options["preCountdownDisplay"];
            self.preCountdownTime = self.options["preCountdownTime"];
            self.preCountdownText = self.options["preCountdownText"];

            self.mainCountdownTime = self.options["mainCountdownTime"];
            self.mainCountdownText = self.options["mainCountdownText"];
            self.mainCountdownDisplay = self.options["mainCountdownDisplay"];

            self.displayClass = self.options["displayClass"];

            if (self.preCountdownDisplay) {
                self.el.parentNode.classList.remove('d-none');
            }

            self._checkTimer();
            self.interval = setInterval(function () { self._checkTimer(); }, 1000);
        });
    },

    /**
     * @private
     */
    _checkTimer: function () {
        var now = new Date();

        var remainingPreSeconds = this.preCountdownTime - (now.getTime()/1000);
        if (remainingPreSeconds <= 1) {
            this.el.querySelector('.o_countdown_text').textContent = this.mainCountdownText;
            if (this.mainCountdownDisplay) {
                this.el.parentNode.classList.remove('d-none');
            }
            var remainingMainSeconds = this.mainCountdownTime - (now.getTime()/1000);
            if (remainingMainSeconds <= 1) {
                clearInterval(this.interval);
                document.querySelector(this.displayClass).classList.remove('d-none');
                this.el.parentNode.classList.add('d-none');
            } else {
                this._updateCountdown(remainingMainSeconds);
            }
        } else {
            this._updateCountdown(remainingPreSeconds);
        }
    },

    /**
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

        this.el.querySelector("span.o_timer_days").textContent = days;
        this.el.querySelector("span.o_timer_hours").textContent = this._zeroPad(hours, 2);
        this.el.querySelector("span.o_timer_minutes").textContent = this._zeroPad(minutes, 2);
        this.el.querySelector("span.o_timer_seconds").textContent = this._zeroPad(remainingSeconds, 2);
    },

    /**
     * @private
     */
    _zeroPad: function (num, places) {
      var zero = places - num.toString().length + 1;
      return new Array(+(zero > 0 && zero)).join("0") + num;
    },

});

export default publicWidget.registry.countdownWidget;
