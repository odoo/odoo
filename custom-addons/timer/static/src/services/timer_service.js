/** @odoo-module */

import { deserializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";

const { DateTime, Interval } = luxon;

class TimerService {
    constructor(orm) {
        this.orm = orm;
        this.clearTimer();
    }

    get toSeconds() {
        return (this.hours * 60 + this.minutes) * 60 + this.seconds;
    }

    get floatValue() {
        return this.toSeconds / 3600;
    }

    get timerFormatted() {
        const hours = `${this.hours}`.padStart(2, "0");
        const minutes = `${this.minutes}`.padStart(2, "0");
        const seconds = `${this.seconds}`.padStart(2, "0");
        return `${hours}:${minutes}:${seconds}`;
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

    computeOffset(time) {
        const { seconds } = this.getInterval(DateTime.now(), time)
            .toDuration(["seconds", "milliseconds"])
            .toObject();
        this.offset = seconds;
    }

    setTimer(timeElapsed, timerStart, serverTime) {
        this.resetTimer();
        this.addFloatTime(timeElapsed);
        this.timeElapsed = this.toSeconds;
        if (timerStart && serverTime) {
            const dateStart = timerStart;
            const { hours, minutes, seconds } = this.getInterval(dateStart, serverTime)
                .toDuration(["hours", "minutes", "seconds", "milliseconds"]) // avoid having milliseconds in seconds attribute
                .toObject();
            this.addHours(hours);
            this.addMinutes(minutes);
            this.addSeconds(seconds);
        } else if ((timerStart && !serverTime) || (!timerStart && serverTime)) {
            console.error(
                "Missing parameter: the timerStart or serverTime when one of them is defined."
            );
        }
    }

    getInterval(dateA, dateB) {
        let startDate, endDate;
        if (dateA <= dateB) {
            startDate = dateA;
            endDate = dateB;
        } else {
            startDate = dateB;
            endDate = dateA;
        }
        return Interval.fromDateTimes(startDate, endDate);
    }

    getCurrentTime() {
        return DateTime.now().plus({ seconds: this.offset });
    }

    async getServerTime() {
        const serverTime = deserializeDateTime(
            await this.orm.call("timer.timer", "get_server_time")
        );
        return serverTime.setZone("utc");
    }

    addFloatTime(timeElapsed) {
        if (timeElapsed === 0) {
            this.hours = this.minutes = this.seconds = 0;
            return;
        }

        const minutes = timeElapsed % 1;
        this.hours = timeElapsed - minutes;
        this.minutes = minutes * 60;
    }

    updateTimer(timerStart) {
        const currentTime = this.getCurrentTime();
        const timeElapsed = this.getInterval(timerStart, currentTime);
        const { seconds } = timeElapsed.toDuration(["seconds", "milliseconds"]).toObject();
        this.addSeconds(seconds - this.toSeconds + this.timeElapsed);
    }

    resetTimer() {
        this.hours = 0;
        this.minutes = 0;
        this.seconds = 0;
    }

    clearTimer() {
        this.resetTimer();
        delete this.offset;
    }
}

export const timerService = {
    dependencies: ["orm"],
    async: [
        "getServerTime",
    ],
    start(env, { orm }) {
        return new TimerService(orm);
    }
};

registry.category('services').add('timer', timerService);
