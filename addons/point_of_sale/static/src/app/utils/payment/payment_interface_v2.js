import { _t } from "@web/core/l10n/translation";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { PaymentPoller } from "@point_of_sale/app/utils/payment/payment_poller";
import { PaymentRequest, REQUEST_DROPPED } from "@point_of_sale/app/utils/payment/payment_request";

export { REQUEST_DROPPED };

/**
 * Implement this interface to support a new payment method in the POS:
 *
 * import { PaymentInterfaceV2 } from "@point_of_sale/app/utils/payment/payment_interface_v2";
 * class MyPayment extends PaymentInterfaceV2 {}
 *
 * import { registry } from "@web/core/registry";
 * registry.category("pos_payment_providers").add("my_payment", MyPayment);
 *
 * my_payment is the technical name of the added selection in payment_provider.
 * New fields can be loaded through the loader_params of `pos.session`.
 *
 * It replaces the line flows of PaymentInterface, the hooks stay. Each action
 * on a line (`line.pay()`, `line.cancelPayment()`, `line.adjustAmount()`)
 * sets a waiting status, calls send*() and gives its result to the matching
 * handle*Response(), or its error to handle*ResponseError(). Those handlers
 * set the final status; `request.wait(status)` can set an intermediate one,
 * handleForceDone() and handleForceCancel() set it on a force. The handlers
 * are awaited, so they can be async. canBeAdjusted() and sendPaymentAdjust()
 * receive the line, not its uuid.
 *
 * Each `line.pay()` starts a PaymentRequest, settled once, see
 * payment_request.js. When the provider answers later, sendPaymentRequest()
 * returns `request.wait(status)`: the webhook gives the answer to
 * answerRequest(), polling (`use_polling`, pollPaymentStatus()) to the
 * request itself. An answer after a force, cancel or error goes to
 * handleLateResponse(), where the cashier can apply it.
 */
export class PaymentInterfaceV2 extends PaymentInterface {
    /**
     * Sets the options of the interface. Override it to change an option or
     * listen to the bus.
     *
     * @prop {boolean} use_polling - while a request waits for its answer
     * (`request.wait()`), ask pollPaymentStatus() for it. False by default:
     * the answer comes from the send or through answerRequest() (webhook).
     * @prop {number} polling_interval - ms between two polls
     * @prop {number|false} max_poll_failures - polls failing in a row before
     * polling gives up and the cashier gets the "Check status" action; false
     * for no limit
     * @prop {number|false} max_polling_duration - ms of polling before it gives
     * up, with an error dialog and the "Check status" action; false for no
     * limit
     * @prop {string} title_error - title of the error dialogs, see showError()
     * @prop {Object<string, PaymentRequest>} requests - line uuid -> its last
     * request, until that request is answered and handled (see _forget())
     */
    setup(pos, payment_method_id) {
        super.setup(...arguments);
        this.use_polling = false;
        this.polling_interval = 5000;
        this.max_poll_failures = 3;
        this.max_polling_duration = 5 * 60 * 1000;
        this.title_error = _t("Payment Error");
        this.requests = {};
    }

    // ----- Line Flows -----

    /**
     * Run by `line.pay()`:
     * 1. Starts a new request for the line (the previous one is dropped) and
     *    sets the line to "waiting".
     * 2. sendPaymentRequest() answers directly, or returns `request.wait()`
     *    when the answer comes later (webhook, polling). Either way the
     *    answer goes to `request.answer()`: only the first one counts.
     * 3. Waits for the request to be settled:
     *    - answered: handlePaymentResponse() sets the line status, then the
     *      request is forgotten;
     *    - dropped (forced, cancelled, replaced): returns false, the force,
     *      cancel or new request sets the status.
     *
     * When sendPaymentRequest() throws, handlePaymentResponseError() sets
     * the line to retry and the error is rethrown, unless the request was
     * settled meanwhile: dropped (forced, cancelled), the error is only
     * rethrown; answered (e.g. by the webhook), the answer is handled and the
     * error ignored. An answer after a force, cancel or error goes to
     * handleLateResponse().
     *
     * @returns {Promise<boolean>} true when the order can be validated
     * automatically
     */
    async pay(line) {
        const request = this.newRequest(line);
        line.payment_status = "waiting";
        try {
            request.answer(await this.sendPaymentRequest(line, request));
        } catch (error) {
            if (request.drop("failed")) {
                await this.handlePaymentResponseError(line, error);
                throw error;
            }
            if (request.state !== "answered") {
                throw error; // forced or cancelled meanwhile: the line is settled already
            }
            // Answered while it was being sent (e.g. webhook): the answer counts
        }
        const response = await request.promise;
        if (response === REQUEST_DROPPED) {
            return false;
        }
        try {
            return await this.handlePaymentResponse(line, response);
        } catch (error) {
            await this.handlePaymentResponseError(line, error);
            throw error;
        } finally {
            this._forget(request);
        }
    }

    /**
     * Run by `line.cancelPayment()`:
     * 1. Returns false when the request of the line is settled already
     *    (answered or dropped). A line without a request (sent from another
     *    device, not restored, or answered and handled) can still be
     *    cancelled.
     * 2. Sets the line to "waiting_cancel" and calls sendPaymentCancel().
     * 3. handlePaymentCancelResponse() sets the line status: "retry" when
     *    cancelled, back to the status before the cancel otherwise. When
     *    cancelled, the request is dropped: a waiting `line.pay()` returns
     *    false.
     *
     * When sendPaymentCancel() throws, handlePaymentCancelResponseError()
     * puts back the status before the cancel and the error is rethrown.
     *
     * When the request is settled while the cancel is sent (answered, maybe
     * still being handled, or forced), the cancel changes nothing, whatever
     * its result or error: it returns false and leaves the status to the
     * answer or the force. Answered while handlePaymentCancelResponse() is
     * awaited, the cancel returns false too, so the handler must set the
     * status before it awaits anything. An answer after a successful cancel
     * goes to handleLateResponse().
     *
     * @returns {Promise<boolean>} true when the payment was cancelled
     */
    async cancelPayment(line) {
        const request = this.requests[line.uuid];
        if (request && !request.isPending) {
            return false;
        }
        const previousStatus = line.payment_status;
        line.payment_status = "waiting_cancel";
        // Answered (maybe still being handled) or forced during the cancel:
        // the cancel must not overwrite it
        const isSettledMeanwhile = () => request && !request.isPending;
        try {
            const response = await this.sendPaymentCancel(line);
            if (isSettledMeanwhile()) {
                return false;
            }
            const isCancelled = await this.handlePaymentCancelResponse(
                line,
                response,
                previousStatus
            );
            if (!isCancelled) {
                return false;
            }
            // Answered while the handler was awaited: the answer wins
            return !request || request.drop("cancelled");
        } catch (error) {
            if (isSettledMeanwhile()) {
                return false;
            }
            await this.handlePaymentCancelResponseError(line, error, previousStatus);
            throw error;
        }
    }

    /**
     * Run by `line.forceDone()`, when the cashier knows the payment went
     * through (e.g. seen on the terminal). Drops the request of the line, so
     * a waiting `line.pay()` returns false, then handleForceDone() sets the
     * line to "done". Does nothing when the request is settled already
     * (answered or dropped). An answer that comes after goes to
     * handleLateResponse().
     */
    forceDone(line) {
        if (this._dropRequest(line, "forced")) {
            this.handleForceDone(line);
        }
    }

    /**
     * Run by `line.forceCancel()`, when the cashier gives up on the payment
     * (e.g. the cancel gets no answer). Drops the request of the line, so a
     * waiting `line.pay()` or cancelPayment() returns false, then
     * handleForceCancel() sets the line to "retry". Does nothing when the
     * request is settled already (answered or dropped). An answer that comes
     * after goes to handleLateResponse().
     */
    forceCancel(line) {
        if (this._dropRequest(line, "forced")) {
            this.handleForceCancel(line);
        }
    }

    /**
     * canBeAdjusted() and sendPaymentAdjust() receive the line itself, see
     * PaymentInterface._adjustHookArg().
     */
    _adjustHookArg(line) {
        return line;
    }

    // ----- Payment Request -----

    /**
     * Sends the payment request. The line is "waiting" meanwhile; an
     * intermediate status (waiting_card, waiting_scan, waiting_capture) can
     * be set here.
     *
     * Resolve with the answer when it comes within the request (SDK callback,
     * device socket), or return `request.wait(status)` when it comes later.
     * On success, set card_type and transaction_id on the line.
     *
     * @param {Object} line
     * @param {PaymentRequest} request
     * @returns {Promise} the provider's response, given to
     * `request.answer()` then handlePaymentResponse(). By default a boolean,
     * false to retry.
     */
    async sendPaymentRequest(line, request) {}

    /**
     * Whether the provider's response says the payment went through. Used
     * for late answers, see handleLateResponse(). By default a boolean.
     *
     * @returns {boolean}
     */
    isPaymentSuccessful(line, response) {
        return Boolean(response);
    }

    /**
     * Called once per request with an answer that comes after the request
     * was dropped (forced, cancelled, failed, replaced):
     * - the answer agrees with the line (e.g. paid after a force done): when
     *   paid, it is applied silently for what it brings (transaction id,
     *   tip, ...), see applyLateResponse(); refused, nothing to do;
     * - it contradicts the line (e.g. paid after a force cancel): the cashier
     *   chooses to apply it or keep the line as it is.
     * When the line can't change anymore (order validated, line removed, or
     * a newer request of the line), the cashier is only told, and only when
     * the answer means money to reverse or missing.
     */
    async handleLateResponse(line, response, request) {
        const isPaid = this.isPaymentSuccessful(line, response);
        const order = line.pos_order_id;
        const isCurrent = this.requests[line.uuid] === request;
        if (isCurrent && order && isPaid === (line.payment_status === "done")) {
            if (isPaid && !order.finalized) {
                await this.applyLateResponse(line, response, request, { autoValidate: false });
            }
            return;
        }
        const params = {
            amount: formatCurrency(line.getAmount(), order ? line.currency : this.pos.currency),
            order: order?.floatingOrderName,
        };
        if (!isCurrent || !order) {
            if (isPaid) {
                this.showError(
                    _t(
                        "A transaction of %(amount)s was accepted after its payment was cancelled or removed in the POS. Reverse it on the terminal or with the payment provider.",
                        params
                    )
                );
            }
            return;
        }
        if (order.finalized) {
            this.showError(
                isPaid
                    ? _t(
                          "The transaction of %(amount)s for order %(order)s was accepted, but the order was validated without it. Reverse it on the terminal or with the payment provider.",
                          params
                      )
                    : _t(
                          "The transaction of %(amount)s for order %(order)s was refused, but the order was validated with it. The amount was not paid.",
                          params
                      )
            );
            return;
        }
        let body;
        if (!isPaid) {
            body = _t(
                "The transaction of %(amount)s for order %(order)s was refused after the payment was forced as done in the POS. If you keep it as paid, the amount is missing.",
                params
            );
        } else if (request.state === "failed") {
            body = _t(
                "The transaction of %(amount)s for order %(order)s was accepted after the payment failed in the POS. If you keep it as not paid, reverse it on the terminal or with the payment provider.",
                params
            );
        } else {
            body = _t(
                "The transaction of %(amount)s for order %(order)s was accepted after the payment was cancelled in the POS. If you keep it as not paid, reverse it on the terminal or with the payment provider.",
                params
            );
        }
        this.dialog.add(ConfirmationDialog, {
            title: this.title_error,
            body,
            confirmLabel: isPaid ? _t("Mark as paid") : _t("Mark as not paid"),
            cancelLabel: isPaid ? _t("Keep as not paid") : _t("Keep as paid"),
            confirm: () => this.applyLateResponse(line, response, request),
            cancel: () => {},
        });
    }

    /**
     * Handles a late answer as if it came in time: the only way a dropped
     * request becomes answered. Does nothing when the line started another
     * request, was removed, or its order was validated meanwhile.
     *
     * @param {Object} line
     * @param {any} response
     * @param {PaymentRequest} request - the dropped request it answers
     * @param {Object} [options]
     * @param {boolean} [options.autoValidate=true] - false to leave the
     * order as it is when the payment is accepted, see
     * _handleUnawaitedAnswer()
     */
    async applyLateResponse(line, response, request, { autoValidate = true } = {}) {
        const order = line.pos_order_id;
        if (this.requests[line.uuid] !== request || !order || order.finalized) {
            return;
        }
        request.state = "answered";
        await this._handleUnawaitedAnswer(request, response, { autoValidate });
    }

    // ----- Payment Adjust -----

    /**
     * Whether the amount authorized for the line can still be adjusted.
     *
     * @returns {boolean}
     */
    canBeAdjusted(line) {
        return false;
    }

    /**
     * Adjusts the authorized amount (tip, new order line). The line already
     * holds the new amount and is "waiting" meanwhile. When the provider
     * refuses, show the reason: callers only get false.
     *
     * @returns {Promise} the provider's response, given to
     * handlePaymentAdjustResponse(). By default a boolean, true when adjusted.
     */
    async sendPaymentAdjust(line) {}

    // ----- Waiting For The Response -----

    /**
     * Starts a new request for the line, called by `line.pay()` and on load.
     * The previous request of the line is dropped ("replaced"): an answer to
     * it goes to handleLateResponse(), which can't change the line anymore.
     *
     * @returns {PaymentRequest}
     */
    newRequest(line) {
        this.requests[line.uuid]?.drop("replaced");
        const request = new PaymentRequest(line, {
            onLateAnswer: (response) => this.handleLateResponse(line, response, request),
        });
        if (this.use_polling) {
            request.poller = new PaymentPoller({
                poll: () => this.pollPaymentStatus(line),
                onAnswer: (response) => request.answer(response),
                onGiveUp: (reason) => this._onPollingGiveUp(line, reason),
                isActive: () => line.isProcessing,
                interval: this.polling_interval,
                maxFailures: this.max_poll_failures,
                maxDuration: this.max_polling_duration,
            });
        }
        this.requests[line.uuid] = request;
        return request;
    }

    /**
     * Whether a request of this interface can still get an answer, see
     * connectWebhook().
     */
    get expectsAnswer() {
        return Object.values(this.requests).some((request) => request.expectsAnswer);
    }

    /**
     * Listens to the bus `channel` the server notifies when the provider's
     * webhook is received. One listener for all the payment methods of the
     * provider: each interface of `PaymentClass` that expects an answer gets
     * onWebhookNotification().
     *
     * @param {string} channel
     * @param {typeof PaymentInterfaceV2} PaymentClass
     */
    connectWebhook(channel, PaymentClass) {
        this.connectWebSocket(channel, (payload) =>
            this.pos.models["pos.payment.method"]
                .filter(
                    ({ payment_interface }) =>
                        payment_interface instanceof PaymentClass && payment_interface.expectsAnswer
                )
                .forEach(({ payment_interface }) =>
                    payment_interface.onWebhookNotification(payload)
                )
        );
    }

    /**
     * Called for each notification of connectWebhook(): read the answer,
     * find its line and give it to answerRequest(). The line can be settled
     * already: the answer is then late, see handleLateResponse().
     *
     * @param {any} payload - what the server sent on the bus
     */
    async onWebhookNotification(payload) {}

    /**
     * Gives the provider's answer (webhook, ...) to the last request of the
     * line, see PaymentRequest.answer(). Only give it a final answer: the
     * first one settles the request. As for pollPaymentStatus(), undefined
     * means no result yet and is ignored. Ignored too when the line has no
     * request (sent from another device, not restored, or answered and
     * handled).
     *
     * @param {Object} line
     * @param {any} response
     */
    answerRequest(line, response) {
        if (response !== undefined) {
            this.requests[line.uuid]?.answer(response);
        }
    }

    /**
     * Asks the provider for the status of the line, every `polling_interval`
     * ms while it is processing, when `use_polling` is set, and once from
     * checkPaymentStatus(). A rejection counts as a failed poll (see
     * `max_poll_failures`); from checkPaymentStatus() it is rethrown.
     *
     * @returns {Promise<any>} the answer, given to the request (see
     * PaymentRequest.answer()), or undefined while there is no result yet
     */
    async pollPaymentStatus(line) {}

    /**
     * Reads the status once, when the cashier asks for it after polling gave
     * up. Polling resumes when there is no result yet. A failed read sets
     * the "Check status" action again and is rethrown, so the global error
     * handler shows it. Without a pending request (e.g. after a reload
     * without restore), only removes the action.
     */
    async checkPaymentStatus(line) {
        delete line.uiState.statusCheckNeeded;
        const request = this.requests[line.uuid];
        if (!request?.isPending) {
            return;
        }
        let response;
        try {
            response = await this.pollPaymentStatus(line);
        } catch (error) {
            if (request.isPending) {
                line.uiState.statusCheckNeeded = true;
            }
            throw error;
        }
        if (response === undefined) {
            request.wait();
        } else {
            request.answer(response);
        }
    }

    /**
     * Called on load (pos_store.restorePendingPayments()) for each line still
     * processing of an order not validated: its `line.pay()` was lost with
     * the page. Starts a new request and waits for its answer again, keeping
     * the line status: polling resumes when `use_polling` is set, and
     * answerRequest() (webhook) can answer it. Then:
     * - answered: see _handleUnawaitedAnswer();
     * - dropped (forced, cancelled, replaced): nothing, the force, cancel or
     *   new request sets the status.
     * Without polling or webhook, the line waits for the cashier to cancel
     * or force it.
     */
    async restorePendingRequest(line) {
        const request = this.newRequest(line);
        const response = await request.wait();
        if (response !== REQUEST_DROPPED) {
            await this._handleUnawaitedAnswer(request, response);
        }
    }

    /**
     * Called when the polling of the line gives up, see PaymentPoller. The
     * request stays pending: the line shows the "Check status" action (see
     * checkPaymentStatus()), and a webhook, a cancel or a force can still
     * settle it.
     *
     * @param {Object} line
     * @param {"failures"|"duration"} reason - `max_poll_failures` polls
     * failed in a row (the cashier sees the error when checking the status),
     * or `max_polling_duration` passed (an error dialog says so)
     */
    _onPollingGiveUp(line, reason) {
        if (reason === "duration") {
            this.showError(
                _t(
                    "No answer from the payment provider yet. Check the terminal, or check the status."
                )
            );
        }
        // The "Check status" action of the line shows the error
        line.uiState.statusCheckNeeded = true;
    }

    /**
     * Handles an answer no `line.pay()` waits for (reload, late answer), as
     * pay() does: handlePaymentResponse() sets the line status, or
     * handlePaymentResponseError() when it throws (the error is rethrown).
     * When accepted, `pos.onPaymentAccepted()` validates the order or
     * notifies. The request is then forgotten.
     *
     * @param {PaymentRequest} request - answered
     * @param {any} response
     * @param {Object} [options]
     * @param {boolean} [options.autoValidate=true] - false to skip
     * `pos.onPaymentAccepted()`
     */
    async _handleUnawaitedAnswer(request, response, { autoValidate = true } = {}) {
        const line = request.line;
        try {
            if ((await this.handlePaymentResponse(line, response)) && autoValidate) {
                this.pos.onPaymentAccepted?.(line);
            }
        } catch (error) {
            await this.handlePaymentResponseError(line, error);
            throw error;
        } finally {
            this._forget(request);
        }
    }

    /**
     * Forgets an answered request once handled: nothing can change it
     * anymore, and a line without a request ignores other answers.
     */
    _forget(request) {
        if (this.requests[request.line.uuid] === request) {
            delete this.requests[request.line.uuid];
        }
    }

    /**
     * Drops the last request of the line, see PaymentRequest.drop().
     *
     * @returns {boolean} false when that request was settled already. A line
     * without a request (sent from another device, not restored, or answered
     * and handled) can always be dropped.
     */
    _dropRequest(line, state) {
        return this.requests[line.uuid]?.drop(state) ?? true;
    }

    // ----- Helpers -----

    /**
     * Shows an error dialog.
     *
     * @param {string} message
     * @param {string} [title] - `title_error` by default
     * @param {Object} [options] - Other AlertDialog props
     */
    showError(message, title = this.title_error, options = {}) {
        this.dialog.add(AlertDialog, { title, body: message, ...options });
    }
}
