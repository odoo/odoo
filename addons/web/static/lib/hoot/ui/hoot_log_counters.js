/** @odoo-module */

import { Component, props, types as t, xml } from "@odoo/owl";

export class HootLogCounters extends Component {
    static template = xml`
        <t t-if="this.props.logs.error">
            <span
                class="flex items-center gap-1 text-rose"
                t-attf-title="{{ this.props.logs.error }} error log(s) (check the console)"
            >
                <i class="fa fa-times-circle" />
                <strong t-out="this.props.logs.error" />
            </span>
        </t>
        <t t-if="this.props.logs.warn">
            <span
                class="flex items-center gap-1 text-amber"
                t-attf-title="{{ this.props.logs.warn }} warning log(s) (check the console)"
            >
                <i class="fa fa-exclamation-triangle" />
                <strong t-out="this.props.logs.warn" />
            </span>
        </t>
    `;

    // Props & plugins
    props = props({
        logs: t.object({
            error: t.number(),
            warn: t.number(),
        }),
    });
}
