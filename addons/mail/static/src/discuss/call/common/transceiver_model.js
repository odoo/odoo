/** @odoo-module */

export class Transceiver {
    constructor({ kind, target, sessionId, rtcTransceiver }) {
        this.kind = kind;
        this.target = target;
        this.sessionId = sessionId;
        this.rtcTransceiver = rtcTransceiver;
    }

    get mid() {
        return this.rtcTransceiver?.mid;
    }

    get direction() {
        return this.rtcTransceiver?.direction;
    }

    set direction(direction) {
        this.rtcTransceiver.direction = direction;
    }

    get receiver() {
        return this.rtcTransceiver?.receiver;
    }

    get sender() {
        return this.rtcTransceiver?.sender;
    }
}
