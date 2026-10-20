/**
 * What wait() and `promise` resolve with when the request is dropped (forced,
 * cancelled, failed, replaced); `line.pay()` then returns false.
 */
export const REQUEST_DROPPED = Symbol("REQUEST_DROPPED");

/**
 * One payment request of a line, see PaymentInterfaceV2.newRequest().
 *
 * It is settled once, by the first of:
 * - answer(): the answer of the provider ("answered"),
 * - drop(): a force ("forced"), a successful cancel ("cancelled"), an error
 *   while sending ("failed"), a new request of the line ("replaced").
 *
 * Whatever comes after changes nothing: a second answer is ignored, a second
 * drop does nothing. Only an answer after a drop counts, once: it is given
 * to `onLateAnswer`.
 */
export class PaymentRequest {
    /**
     * @param {Object} line - the pos.payment
     * @param {Object} [options]
     * @param {Function} [options.onLateAnswer] - called with an answer that
     * comes after a drop
     */
    constructor(line, { onLateAnswer = () => {} } = {}) {
        this.line = line;
        this.state = "pending";
        this.poller = null; // a PaymentPoller, when the provider polls
        this.hasLateAnswer = false;
        this.onLateAnswer = onLateAnswer;
        this.promise = new Promise((resolve) => (this._resolve = resolve));
    }

    /**
     * Whether the request is not settled yet: no answer, no drop.
     */
    get isPending() {
        return this.state === "pending";
    }

    /**
     * Whether an answer would still change something: pending, or dropped
     * and no late answer yet.
     */
    get expectsAnswer() {
        return this.state !== "answered" && !this.hasLateAnswer;
    }

    /**
     * Waits for the answer: sets the line to `status` (e.g. "waiting_card"),
     * removes the "Check status" action and starts polling, or restarts it
     * from scratch. Does nothing when settled already.
     *
     * @param {string} [status]
     * @returns {Promise} the answer, or REQUEST_DROPPED
     */
    wait(status) {
        if (this.isPending) {
            if (status) {
                this.line.payment_status = status;
            }
            delete this.line.uiState.statusCheckNeeded;
            this.poller?.start();
        }
        return this.promise;
    }

    /**
     * Gives the answer of the provider, from any source (send, webhook,
     * poll, status check). The first one settles the request; a second one
     * is ignored. After a drop, the first answer goes to `onLateAnswer`,
     * the next ones are ignored. REQUEST_DROPPED (what wait() resolves with
     * once dropped) is always ignored.
     *
     * @param {any} response
     */
    answer(response) {
        if (response === REQUEST_DROPPED) {
            return; // what wait() resolves with once dropped
        }
        if (this._settle("answered")) {
            this._resolve(response);
        } else if (this.expectsAnswer) {
            this.hasLateAnswer = true;
            this.onLateAnswer(response);
        }
    }

    /**
     * Settles the request without an answer: wait() and `promise` resolve
     * with REQUEST_DROPPED, so a waiting `line.pay()` returns false.
     *
     * @param {"forced"|"cancelled"|"failed"|"replaced"} state
     * @returns {boolean} false when settled already
     */
    drop(state) {
        if (!this._settle(state)) {
            return false;
        }
        this._resolve(REQUEST_DROPPED);
        return true;
    }

    /**
     * Sets the final state, stops polling and removes the "Check status"
     * action. The promise is resolved by answer() or drop().
     *
     * @returns {boolean} false when settled already
     */
    _settle(state) {
        if (!this.isPending) {
            return false;
        }
        this.state = state;
        this.poller?.stop();
        delete this.line.uiState.statusCheckNeeded;
        return true;
    }
}
