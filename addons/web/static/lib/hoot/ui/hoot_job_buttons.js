/** @odoo-module */

import { Component, xml } from "@odoo/owl";
import { Job } from "../core/job";
import { Test } from "../core/test";
import { HootLink } from "./hoot_link";

/**
 * @typedef {{
 *  hidden?: boolean;
 *  job: Job;
 * }} HootJobButtonsProps
 */

/** @extends {Component<HootJobButtonsProps, import("../hoot").Environment>} */
export class HootJobButtons extends Component {
    static components = { HootLink };

    static props = {
        hidden: { type: Boolean, optional: true },
        job: Job,
    };

    static template = xml`
        <t t-set="type" t-value="getType()" />
        <div class="${HootJobButtons.name} items-center gap-1" t-att-class="props.hidden ? 'hidden' : 'flex'">
            <HootLink
                type="type"
                id="props.job.id"
                class="'hoot-btn-link border border-primary text-emerald rounded transition-colors'"
                title="'Run this ' + type + ' only'"
            >
                <i class="fa fa-play w-5 h-5" />
            </HootLink>
            <t t-if="type === 'test'">
                <HootLink
                    type="type"
                    id="props.job.id"
                    options="{ debug: true }"
                    class="'hoot-btn-link border border-primary text-emerald rounded transition-colors'"
                    title="'Run this ' + type + ' only in debug mode'"
                >
                    <i class="fa fa-bug w-5 h-5" />
                </HootLink>
            </t>
            <HootLink
                type="type"
                id="props.job.id"
                options="{ ignore: true }"
                class="'hoot-btn-link border border-primary text-rose rounded transition-colors'"
                title="'Ignore ' + type"
            >
                <i class="fa fa-ban w-5 h-5" />
            </HootLink>
        </div>
    `;

    getType() {
        return this.props.job instanceof Test ? "test" : "suite";
    }
}
