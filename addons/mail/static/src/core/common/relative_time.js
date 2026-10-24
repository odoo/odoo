import { computedUntilStale } from "@mail/utils/common/signal";

import { Component, types, useProps, xml } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

export class RelativeTime extends Component {
    static template = xml`<t t-out="this.relativeTime()"/>`;

    setup() {
        super.setup();
        this.props = useProps(this.getPropsDefinition());
        this.relativeTime = computedUntilStale(
            () => {
                const delta = Date.now() - this.props.datetime().ts;
                if (Math.abs(delta) < 45 * 1000) {
                    return delta < 0 ? _t("in a few seconds") : _t("now");
                }
                return this.props.datetime().toRelative();
            },
            () => {
                const absDelta = Math.abs(Date.now() - this.props.datetime().ts);
                return absDelta < MINUTE ? absDelta : absDelta < HOUR ? MINUTE : HOUR;
            }
        );
    }

    getPropsDefinition() {
        return {
            datetime: types.signal(types.instanceOf(luxon.DateTime)),
        };
    }
}
