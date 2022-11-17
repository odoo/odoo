/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { Message } from "@mail/core/common/message_model";


patch(Message.prototype, "mass_mailing", {
    get statusIndicatorTitle() {
        return this.failureTraces.length > 0 ? _t('Failed Mass Mailing') : this._super();
    },

    get statusIndicatorIcon() {
        if (this.failureTraces.length) {
            return "fa fa-envelope";
        }
        if (this.traces.length) {
            return "fa fa-envelope-o";
        }
        return this._super();
    },

    get failureTraces() {
        return this.traces.filter(trace => trace.isFailure);
    },

    get hasStatusIndicator() {
        return this._super() || this.traces.length > 0;
    },

    get isSuccess() {
        return this._super() && this.failureTraces.length === 0;
    },
});
