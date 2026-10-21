/**
 * Calls `poll()` every `interval` ms until it gives an answer (anything but
 * undefined), `isActive()` turns false, `maxFailures` polls in a row fail or
 * `maxDuration` ms pass. The last two call `onGiveUp(reason)`. A poll never
 * overlaps the previous one.
 */
export class PaymentPoller {
    /**
     * @param {Object} options
     * @param {Function} options.poll - async, the answer or undefined while
     * there is none yet; a rejection counts as a failed poll
     * @param {Function} options.onAnswer - called with the answer
     * @param {Function} [options.onGiveUp] - called with "failures" or "duration"
     * @param {Function} [options.isActive] - polling stops when it returns false
     * @param {number} [options.interval] - ms
     * @param {number|false} [options.maxFailures] - false for no limit
     * @param {number|false} [options.maxDuration] - ms, false for no limit
     */
    constructor({
        poll,
        onAnswer,
        onGiveUp = () => {},
        isActive = () => true,
        interval = 5000,
        maxFailures = 3,
        maxDuration = false,
    }) {
        this.poll = poll;
        this.onAnswer = onAnswer;
        this.onGiveUp = onGiveUp;
        this.isActive = isActive;
        this.interval = interval;
        this.maxFailures = maxFailures;
        this.maxDuration = maxDuration;
        this.run = null; // { timer, startedAt, failures, busy }
    }

    /**
     * Starts polling, or restarts it from scratch.
     */
    start() {
        this.stop();
        const run = { timer: null, startedAt: Date.now(), failures: 0, busy: false };
        run.timer = setInterval(() => this._tick(run), this.interval);
        this.run = run;
    }

    /**
     * Stops polling. A poll in flight is ignored when it returns.
     */
    stop() {
        clearInterval(this.run?.timer);
        this.run = null;
    }

    /**
     * @param {"failures"|"duration"} reason
     */
    _giveUp(reason) {
        this.stop();
        this.onGiveUp(reason);
    }

    /**
     * One poll of `run`, skipped while the previous one is still in flight.
     *
     * @param {Object} run - the run that started it, see start()
     */
    async _tick(run) {
        if (!this.isActive()) {
            this.stop();
            return;
        }
        if (run.busy) {
            return;
        }
        if (this.maxDuration && Date.now() - run.startedAt >= this.maxDuration) {
            this._giveUp("duration");
            return;
        }
        run.busy = true;
        try {
            const answer = await this.poll();
            run.failures = 0;
            // Not when stopped or restarted meanwhile
            if (this.run === run && answer !== undefined && this.isActive()) {
                this.stop();
                this.onAnswer(answer);
            }
        } catch {
            run.failures++;
            if (this.run === run && this.maxFailures && run.failures >= this.maxFailures) {
                this._giveUp("failures");
            }
        } finally {
            run.busy = false;
        }
    }
}
