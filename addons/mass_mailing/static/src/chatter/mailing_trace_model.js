/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { assignDefined } from "@mail/utils/common/misc";

const statusToClassDict = {
    outgoing: 'fa fa-send-o',
    sent: 'fa fa-check',
    open: 'fa fa-check',
    reply: 'fa fa-check',
    bounce: 'fa fa-exclamation',
    error: 'fa fa-exclamation',
    cancel: 'fa fa-trash-o',
};

const statusToIconTitleDict = {
    outgoing: _t("Outgoing"),
    sent: _t("Sent"),
    open: _t("Opened by Recipient"),
    reply: _t("Reply Received"),
    bounce: _t("Bounced"),
    error: _t("Error"),
    cancel: _t("Canceled"),
};


/**
 * @typedef IMailingTrace
 * @property {number} id
 * @property {string} email
 * @property {string} failure_type
 * @property {number} mailing_id
 * @property {string} trace_type
 * @property {string} trace_status
 */

export class MailingTrace {

    /**
     * @param {IMailingTrace} data
     */
    constructor(data) {
        assignDefined(this, data, [
            'id',
            'email',
            'failure_type',
            'mailing_id',
            'trace_type',
            'trace_status',
        ]);
    }

    get statusIconClass() {
        return statusToClassDict[this.trace_status] ? statusToClassDict[this.trace_status] : '';
    }

    get statusIconTitle() {
        return statusToIconTitleDict[this.trace_status] ? statusToIconTitleDict[this.trace_status] : '';
    }

    get isFailure() {
        return !!this.failure_type || ['bounce', 'cancel'].includes(this.trace_status);
    }
}
