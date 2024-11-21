/** @odoo-module */

import { Component, xml } from "@odoo/owl";

/**
 * @typedef {{
 *  logs: { error: number, warn: number };
 * }} HootLogCountersProps
 */

/** @extends {Component<HootLogCountersProps, import("../hoot").Environment>} */
export class HootLogCounters extends Component {
    static components = {};
    static props = {
        logs: {
            type: Object,
            shape: {
                error: Number,
                warn: Number,
            },
        },
    };
    static template = xml`
        <t t-if="props.logs.error">
            <span
                class="flex items-center gap-1 text-fail"
                t-attf-title="{{ props.logs.error }} error log(s) (check the console)"
            >
                <i class="fa fa-times-circle" />
                <strong t-esc="props.logs.error" />
            </span>
        </t>
        <t t-if="props.logs.warn">
            <span
                class="flex items-center gap-1 text-abort"
                t-attf-title="{{ props.logs.warn }} warning log(s) (check the console)"
            >
                <i class="fa fa-exclamation-triangle" />
                <strong t-esc="props.logs.warn" />
            </span>
        </t>
    `;
}
