odoo.define('timer.Timer', function (require) {
"use strict";

    /**
     * This class improves the timer display using the
     * unit_amount field on account.analytic.line.
     */
    class Timer {
        constructor(hours, minutes, seconds) {
            this.hours = hours;
            this.minutes = minutes;
            this.seconds = seconds;
        }

        /**
         * Convert float to time
         * @param {number} float
         */
        static convertFloatToTime(float) {
            if (float === 0) {
                return new Timer(0, 0, 0);
            }

            let minutes = float % 1;
            const hours = float - minutes;
            minutes *= 60;

            return new Timer(hours, Math.round(minutes), 0);
        }

        /**
         * Create timer
         * @param {number} unit_amount
         * @param {String} timer_start
         * @param {String} serverTime
         */
        static createTimer(unit_amount, timer_start, serverTime) {
            const timer = this.convertFloatToTime(unit_amount);

            timer.addTime(
                moment.utc(
                    moment.utc(serverTime)
                        .diff(moment.utc(timer_start))
                    ).format("HH:mm:ss")
            );

            return timer;
        }

        addHours(hours) {
            this.hours += hours;
        }

        addMinutes(minutes) {
            minutes += this.minutes;

            this.minutes = minutes % 60;
            this.addHours(Math.floor(minutes / 60));
        }

        addSeconds(seconds) {
            seconds += this.seconds;
            this.seconds = seconds % 60;
            this.addMinutes(Math.floor(seconds / 60));
        }

        display2digits(number) {
            return number > 9 ? "" + number : "0" + number;
        }

        addSecond() {
            this.seconds += 1;
            if (this.seconds === 60) {
                this.minutes += 1;
                this.seconds = 0;

                if (this.minutes === 60) {
                    this.hours += 1;
                    this.minutes = 0;
                }
            }
        }

        addTime(time) {
            if (typeof time == 'string' && time.indexOf(':') !== -1) {
                let [hour, minute, second] = time.split(':');

                hour = parseInt(hour);
                minute = parseInt(minute);
                second = parseInt(second);

                this.addSeconds(second);
                this.addMinutes(minute);
                this.addHours(hour);
            }
        }

        convertToFloat() {
            return (this.hours * 60 + this.minutes) * 60 / 3600;
        }

        toString() {
            const time = {
                hours: this.display2digits(this.hours),
                minutes: this.display2digits(this.minutes),
                seconds: this.display2digits(this.seconds)
            };

            return `${time.hours}:${time.minutes}:${time.seconds}`;
        }
    }

    return Timer;

});
