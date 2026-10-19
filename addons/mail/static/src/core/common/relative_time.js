import { propComputed } from "@mail/utils/common/hooks";
import { computedUntilStale } from "@mail/utils/common/signal";

import { Component, types, xml } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

export class RelativeTime extends Component {
    static template = xml`<t t-out="this.relativeTime()"/>`;

    setup() {
        super.setup();
        this.datetime = propComputed("datetime", types.instanceOf(luxon.DateTime));
        this.relativeTime = computedUntilStale(
            () => {
                const delta = Date.now() - this.datetime().ts;
                if (Math.abs(delta) < 45 * 1000) {
                    return delta < 0 ? _t("in a few seconds") : _t("now");
                }
                return this.datetime().toRelative();
            },
            () => {
                const absDelta = Math.abs(Date.now() - this.datetime().ts);
                return absDelta < MINUTE ? absDelta : absDelta < HOUR ? MINUTE : HOUR;
            }
        );
    }
}
