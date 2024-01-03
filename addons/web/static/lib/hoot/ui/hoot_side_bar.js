/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { Suite } from "../core/suite";
import { HootJobButtons } from "./hoot_job_buttons";

/**
 * @typedef {{
 *  name: string;
 *  reporting: import("../hoot_utils").Reporting;
 *  selected: boolean;
 *  unfolded: boolean;
 * }} HootSideBarChevronProps
 *
 * @typedef {{
 *  reporting: import("../hoot_utils").Reporting;
 * }} HootSideBarCounterProps
 *
 * @typedef {{
 * }} HootSideBarProps
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Boolean, Object, String } = globalThis;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @extends {Component<HootSideBarChevronProps, import("../hoot").Environment>}
 */
export class HootSideBarSuite extends Component {
    static props = {
        name: String,
        reporting: Object,
        selected: Boolean,
        unfolded: Boolean,
    };

    static template = xml`
        <t t-if="props.reporting.suites">
            <i
                class="fa fa-chevron-right text-xs transition"
                t-att-class="{ 'rotate-90': props.unfolded }"
            />
        </t>
        <span t-att-class="getClassName()" t-esc="props.name" />
    `;

    getClassName() {
        const { reporting, selected } = this.props;
        let className = "truncate transition";
        if (reporting.failed) {
            className += " text-fail";
        } else if (!reporting.tests) {
            className += " opacity-25";
        }
        if (selected) {
            className += " font-bold";
        }
        return className;
    }
}

/**
 * @extends {Component<HootSideBarCounterProps, import("../hoot").Environment>}
 */
export class HootSideBarCounter extends Component {
    static props = { reporting: Object };

    static template = xml`<span class="text-primary" t-esc="props.reporting.tests" />`;
}

/**
 * @extends {Component<HootSideBarProps, import("../hoot").Environment>}
 */
export class HootSideBar extends Component {
    static components = { HootJobButtons, HootSideBarSuite, HootSideBarCounter };

    static props = {};

    static template = xml`
        <div class="${HootSideBar.name} flex-col w-64 h-full overflow-x-hidden overflow-y-auto resize-x shadow bg-gray-200 dark:bg-gray-800 z-1 hidden md:flex">
            <ul>
                <t t-foreach="state.items" t-as="item" t-key="item.id">
                    <li class="flex items-center h-7">
                        <button
                            class="flex items-center w-full h-full px-2"
                            t-att-class="{ 'bg-gray-300 dark:bg-gray-700': state.hovered === item.id or uiState.selectedSuiteId === item.id }"
                            t-attf-style="margin-left: {{ (item.path.length - 1) * 1 + 'rem' }};"
                            t-on-click="() => this.toggleItem(item.id)"
                            t-on-pointerenter="() => state.hovered = item.id"
                            t-on-pointerleave="() => state.hovered = null"
                        >
                            <div class="flex items-center gap-1 flex-1">
                                <HootSideBarSuite
                                    name="item.name"
                                    reporting="item.reporting"
                                    selected="uiState.selectedSuiteId === item.id"
                                    unfolded="state.unfolded.has(item.id)"
                                />
                            </div>
                            <t t-if="state.hovered === item.id">
                                <HootJobButtons job="item" />
                            </t>
                            <t t-else="">
                                <HootSideBarCounter reporting="item.reporting" />
                            </t>
                        </button>
                    </li>
                </t>
            </ul>
        </div>
    `;

    setup() {
        const { runner, ui } = this.env;

        this.uiState = useState(ui);
        this.runnerState = useState(runner.state);
        this.state = useState({
            hovered: null,
            items: [],
            /** @type {Set<string>} */
            unfolded: new Set(),
        });

        runner.beforeAll(() => this.computeItems());
    }

    computeItems() {
        /**
         * @param {Suite} suite
         */
        const addSuite = (suite) => {
            this.state.items.push(suite);
            if (!unfolded.has(suite.id)) {
                return;
            }
            for (const child of suite.jobs) {
                if (suites.includes(child)) {
                    addSuite(child);
                }
            }
        };

        const { suites } = this.runnerState;
        const { unfolded } = this.state;

        this.state.items = [];
        for (const suite of this.env.runner.rootSuites) {
            addSuite(suite);
        }
    }

    /**
     * @param {string} id
     */
    toggleItem(id) {
        if (this.uiState.selectedSuiteId !== id) {
            this.uiState.selectedSuiteId = id;

            if (this.state.unfolded.has(id)) {
                return;
            }
        }

        if (this.state.unfolded.has(id)) {
            this.state.unfolded.delete(id);
        } else {
            this.state.unfolded.add(id);

            const { suites } = this.runnerState;
            let suite = this.env.runner.suites.get(id);
            let filteredJobs = suite.jobs.filter((job) => suites.includes(job));
            while (filteredJobs.length === 1) {
                suite = filteredJobs[0];
                filteredJobs = suite.jobs.filter((job) => suites.includes(job));
                this.state.unfolded.add(suite.id);
            }
        }

        this.computeItems();
    }
}
