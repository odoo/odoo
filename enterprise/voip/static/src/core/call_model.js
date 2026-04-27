import { Record } from "@mail/core/common/record";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

export class Call extends Record {
    static id = "id";
    /** @type {Object.<number, Call>} */
    static records = {};

    /**
     * @param {Object} data
     * @returns {Call}
     */
    update(data) {
        super.update(...arguments);
        if (data.partner) {
            this.partner = this.store.Persona.insert({ ...data.partner, type: "partner" });
        }
        if (data.creationDate) {
            this.creationDate = deserializeDateTime(data.creationDate);
        }
        if (data.startDate) {
            this.startDate = deserializeDateTime(data.startDate);
        }
        if (data.endDate) {
            this.endDate = deserializeDateTime(data.endDate);
        }
    }

    activity;
    /** @type {luxon.DateTime} */
    creationDate;
    /** @type {"incoming"|"outgoing"} */
    direction;
    /** @type {string} */
    displayName;
    /** @type {luxon.DateTime} */
    endDate;
    /** @type {import("@mail/core/persona_model").Persona | undefined} */
    partner;
    /** @type {string} */
    phoneNumber;
    /** @type {luxon.DateTime} */
    startDate;
    /** @type {"aborted"|"calling"|"missed"|"ongoing"|"rejected"|"terminated"} */
    state;
    /** @type {{ interval: number, time: number }} */
    timer;

    /** @returns {string} */
    get callDate() {
        if (this.state === "terminated") {
            return this.startDate.toLocaleString(luxon.DateTime.DATETIME_SHORT);
        }
        return this.creationDate.toLocaleString(luxon.DateTime.DATETIME_SHORT);
    }

    /** @returns {number} */
    get duration() {
        if (!this.startDate || !this.endDate) {
            return 0;
        }
        return (this.endDate - this.startDate) / 1000;
    }

    /** @returns {string} */
    get durationString() {
        if (!this.duration) {
            return "";
        }
        const minutes = Math.floor(this.duration / 60);
        const seconds = this.duration % 60;
        if (minutes === 0) {
            switch (seconds) {
                case 0:
                    return _t("less than a second");
                case 1:
                    return _t("1 second");
                case 2:
                    return _t("2 seconds");
                default:
                    return _t("%(seconds)s seconds", { seconds });
            }
        }
        if (seconds === 0) {
            switch (minutes) {
                case 1:
                    return _t("1 minute");
                case 2:
                    return _t("2 minutes");
                default:
                    return _t("%(minutes)s minutes", { minutes });
            }
        }
        return _t("%(minutes)s min %(seconds)s sec", { minutes, seconds });
    }

    /** @returns {boolean} */
    get isInProgress() {
        switch (this.state) {
            case "calling":
            case "ongoing":
                // In case the power goes out in the middle of a call (for
                // example), the call may be stuck in the “calling” or “ongoing”
                // state, meaning we can't rely on the state alone, hence the
                // need to also check for the session.
                return Boolean(this.store.env.services["voip.user_agent"].session);
            default:
                return false;
        }
    }
}

Call.register();
