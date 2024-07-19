/** @odoo-module */

import { Component, useState, xml } from "@odoo/owl";
import { Suite } from "../core/suite";
import { HootJobButtons } from "./hoot_job_buttons";

/**
 * @typedef {{
 *  multi?: number;
 *  name: string;
 *  hasSuites: boolean;
 *  reporting: import("../hoot_utils").Reporting;
 *  selected: boolean;
 *  unfolded: boolean;
 * }} HootSideBarSuiteProps
 *
 * @typedef {{
 *  reporting: import("../hoot_utils").Reporting;
 *  statusFilter: import("./setup_hoot_ui").StatusFilter | null;
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
 * @extends {Component<HootSideBarSuiteProps, import("../hoot").Environment>}
 */
export class HootSideBarSuite extends Component {
    static props = {
        multi: { type: Number, optional: true },
        name: String,
        hasSuites: Boolean,
        reporting: Object,
        selected: Boolean,
        unfolded: Boolean,
    };

    static template = xml`
        <t t-if="props.hasSuites">
            <i
                class="fa fa-chevron-right text-xs transition"
                t-att-class="{
                    'rotate-90': props.unfolded,
                    'opacity-25': !props.reporting.failed and !props.reporting.tests
                }"
            />
        </t>
        <span t-att-class="getClassName()" t-esc="props.name" />
        <t t-if="props.multi">
            <strong class="text-abort whitespace-nowrap me-1">
                x<t t-esc="props.multi" />
            </strong>
        </t>
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

/** @extends {Component<HootSideBarCounterProps, import("../hoot").Environment>} */
export class HootSideBarCounter extends Component {
    static props = {
        reporting: Object,
        statusFilter: [String, { value: null }],
    };

    static template = xml`
        <t t-set="info" t-value="getCounterInfo()" />
        <span
            t-attf-class="${HootSideBarCounter.name} {{ info[1] ? info[0] : 'text-muted' }} {{ info[1] ? 'font-bold' : '' }}"
            t-esc="info[1]"
        />
    `;

    getCounterInfo() {
        const { reporting, statusFilter } = this.props;
        switch (statusFilter) {
            case "failed":
                return ["text-fail", reporting.failed];
            case "passed":
                return ["text-pass", reporting.passed];
            case "skipped":
                return ["text-skip", reporting.skipped];
            case "todo":
                return ["text-todo", reporting.todo];
            default:
                return ["text-primary", reporting.tests];
        }
    }
}

/**
 * @extends {Component<HootSideBarProps, import("../hoot").Environment>}
 */
export class HootSideBar extends Component {
    static components = { HootJobButtons, HootSideBarSuite, HootSideBarCounter };

    static props = {};

    static template = xml`
        <div
            class="${HootSideBar.name} flex-col w-64 h-full overflow-x-hidden overflow-y-auto resize-x shadow bg-gray-200 dark:bg-gray-800 z-1 hidden md:flex"
            t-on-click="onClick"
        >
            <ul>
                <t t-foreach="state.suites" t-as="suite" t-key="suite.id">
                    <li class="flex items-center h-7 animate-slide-down">
                        <button
                            class="hoot-sidebar-suite flex items-center w-full h-full px-2 overflow-hidden hover:bg-gray-300 dark:hover:bg-gray-700"
                            t-att-class="{ 'bg-gray-300 dark:bg-gray-700': uiState.selectedSuiteId === suite.id }"
                            t-attf-style="margin-left: {{ (suite.path.length - 1) + 'rem' }};"
                            t-attf-title="{{ suite.fullName }}\n- {{ suite.totalTestCount }} tests\n- {{ suite.totalSuiteCount }} suites"
                            t-on-click="() => this.toggleItem(suite.id)"
                        >
                            <div class="flex items-center truncate gap-1 flex-1">
                                <HootSideBarSuite
                                    multi="suite.config.multi"
                                    name="suite.name"
                                    hasSuites="hasSuites(suite)"
                                    reporting="suite.reporting"
                                    selected="uiState.selectedSuiteId === suite.id"
                                    unfolded="state.unfolded.has(suite.id)"
                                />
                                <span class="text-muted">
                                    (<t t-esc="suite.totalTestCount" />)
                                </span>
                            </div>
                            <HootJobButtons hidden="true" job="suite" />
                            <t t-if="env.runner.state.suites.includes(suite)">
                                <HootSideBarCounter
                                    reporting="suite.reporting"
                                    statusFilter="uiState.statusFilter"
                                />
                            </t>
                        </button>
                    </li>
                </t>
            </ul>
        </div>
    `;

    runningSuites = new Set();

    setup() {
        const { runner, ui } = this.env;

        this.uiState = useState(ui);
        this.state = useState({
            suites: [],
            /** @type {Set<string>} */
            unfolded: new Set(),
        });

        runner.beforeAll(() => {
            const singleRootSuite = runner.rootSuites.filter((suite) => suite.currentJobs.length);
            if (singleRootSuite.length === 1) {
                // Unfolds only root suite containing jobs
                this.unfoldAndSelect(singleRootSuite[0]);
            }

            this.computeItems();
        });
    }

    /**
     * @param {PointerEvent} ev
     */
    onClick(ev) {
        if (!ev.target.closest("button")) {
            // Unselect suite when clicking outside of a suite & in the side bar
            this.uiState.selectedSuiteId = null;
            this.uiState.resultsPage = 0;
        }
    }

    computeItems() {
        /**
         * @param {Suite} suite
         */
        const addSuite = (suite) => {
            if (!(suite instanceof Suite)) {
                return;
            }
            this.state.suites.push(suite);
            if (!unfolded.has(suite.id)) {
                return;
            }
            for (const child of suite.jobs) {
                addSuite(child);
            }
        };

        const { unfolded } = this.state;

        this.state.suites = [];
        for (const suite of this.env.runner.rootSuites) {
            addSuite(suite);
        }
    }

    /**
     * @param {import("../core/job").Job} job
     */
    hasSuites(job) {
        return job.jobs.some((subJob) => subJob instanceof Suite);
    }

    /**
     * @param {string} id
     */
    toggleItem(id) {
        if (this.uiState.selectedSuiteId !== id) {
            this.uiState.selectedSuiteId = id;
            this.uiState.resultsPage = 0;

            if (this.state.unfolded.has(id)) {
                return;
            }
        }

        if (this.state.unfolded.has(id)) {
            this.state.unfolded.delete(id);
        } else {
            this.unfoldAndSelect(this.env.runner.suites.get(id));
        }

        this.computeItems();
    }

    /**
     * @param {Suite} suite
     */
    unfoldAndSelect(suite) {
        this.state.unfolded.add(suite.id);

        while (suite.currentJobs.length === 1) {
            suite = suite.currentJobs[0];
            if (!(suite instanceof Suite)) {
                break;
            }
            this.state.unfolded.add(suite.id);
            this.uiState.selectedSuiteId = suite.id;
            this.uiState.resultsPage = 0;
        }
    }
}
