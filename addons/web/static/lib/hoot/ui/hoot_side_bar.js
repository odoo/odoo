/** @odoo-module */

import { Component, onWillRender, useRef, useState, xml } from "@odoo/owl";
import { FOCUSABLE_SELECTOR } from "../../hoot-dom/helpers/dom";
import { Suite } from "../core/suite";
import { createUrlFromId } from "../core/url";
import { lookup, normalize } from "../hoot_utils";
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

const { Boolean, location: actualLocation, Object, String } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const SUITE_CLASSNAME = "hoot-sidebar-suite";

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
            class="${HootSideBar.name} flex-col w-64 h-full resize-x shadow bg-gray-200 dark:bg-gray-800 z-1 hidden md:flex"
            t-on-click="onClick"
        >
            <form class="flex p-2 items-center gap-1">
                <div class="hoot-search-bar border rounded bg-base w-full">
                    <input
                        class="w-full rounded px-2 py-1 outline-none"
                        type="search"
                        placeholder="Search suites"
                        t-ref="search-input"
                        t-model="state.filter"
                        t-on-keydown="onSearchInputKeydown"
                    />
                </div>
                <t t-set="expanded" t-value="unfoldedIds.size === env.runner.suites.size" />
                <button
                    type="button"
                    class="text-primary p-1 transition-colors"
                    t-attf-title="{{ expanded ? 'Collapse' : 'Expand' }} all"
                    t-on-click="() => this.toggleExpand(expanded)"
                >
                    <i t-attf-class="fa fa-{{ expanded ? 'compress' : 'expand' }}" />
                </button>
            </form>
            <ul class="overflow-x-hidden overflow-y-auto" t-ref="suites-list">
                <t t-foreach="filteredSuites" t-as="suite" t-key="suite.id">
                    <li class="flex items-center h-7 animate-slide-down">
                        <button
                            class="${SUITE_CLASSNAME} flex items-center w-full h-full gap-1 px-2 overflow-hidden hover:bg-gray-300 dark:hover:bg-gray-700"
                            t-att-class="{ 'bg-gray-300 dark:bg-gray-700': uiState.selectedSuiteId === suite.id }"
                            t-attf-style="margin-left: {{ (suite.path.length - 1) + 'rem' }};"
                            t-attf-title="{{ suite.fullName }}\n- {{ suite.totalTestCount }} tests\n- {{ suite.totalSuiteCount }} suites"
                            t-on-click="() => this.toggleItem(suite)"
                            t-on-keydown="(ev) => this.onSuiteKeydown(ev, suite)"
                        >
                            <div class="flex items-center truncate gap-1 flex-1">
                                <HootSideBarSuite
                                    multi="suite.config.multi"
                                    name="suite.name"
                                    hasSuites="hasSuites(suite)"
                                    reporting="suite.reporting"
                                    selected="uiState.selectedSuiteId === suite.id"
                                    unfolded="unfoldedIds.has(suite.id)"
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

    filteredSuites = [];
    runningSuites = new Set();
    unfoldedIds = new Set();

    setup() {
        const { runner, ui } = this.env;

        this.searchInputRef = useRef("search-input");
        this.suitesListRef = useRef("suites-list");
        this.uiState = useState(ui);
        this.state = useState({
            filter: "",
            suites: [],
            /** @type {Set<string>} */
            unfoldedIds: new Set(),
        });

        runner.beforeAll(() => {
            const singleRootSuite = runner.rootSuites.filter((suite) => suite.currentJobs.length);
            if (singleRootSuite.length === 1) {
                // Unfolds only root suite containing jobs
                this.unfoldAndSelect(singleRootSuite[0]);
            }
        });

        onWillRender(() => {
            [this.filteredSuites, this.unfoldedIds] = this.getFilteredVisibleSuites();
        });
    }

    /**
     * Filters
     */
    getFilteredVisibleSuites() {
        let allowedIds;
        let unfoldedIds;
        let rootSuites;
        const { runner } = this.env;
        const allSuites = runner.suites.values();

        // Filtering suites

        const nFilter = normalize(this.state.filter);
        if (nFilter) {
            allowedIds = new Set();
            unfoldedIds = new Set(this.state.unfoldedIds);
            rootSuites = new Set();
            for (const matchingSuite of lookup(nFilter, allSuites, "name")) {
                for (const suite of matchingSuite.path) {
                    allowedIds.add(suite.id);
                    unfoldedIds.add(suite.id);
                    if (!suite.parent) {
                        rootSuites.add(suite);
                    }
                }
            }
        } else {
            unfoldedIds = this.state.unfoldedIds;
            rootSuites = runner.rootSuites;
        }

        // Computing unfolded suites

        /**
         * @param {Suite} suite
         */
        const addSuite = (suite) => {
            if (!(suite instanceof Suite) || (allowedIds && !allowedIds.has(suite.id))) {
                return;
            }
            unfoldedSuites.push(suite);
            if (!unfoldedIds.has(suite.id)) {
                return;
            }
            for (const child of suite.jobs) {
                addSuite(child);
            }
        };

        const unfoldedSuites = [];
        for (const suite of rootSuites) {
            addSuite(suite);
        }

        return [unfoldedSuites, unfoldedIds];
    }

    getSuiteElements() {
        return this.suitesListRef.el
            ? [...this.suitesListRef.el.getElementsByClassName(SUITE_CLASSNAME)]
            : [];
    }

    /**
     * @param {import("../core/job").Job} job
     */
    hasSuites(job) {
        return job.jobs.some((subJob) => subJob instanceof Suite);
    }

    /**
     * @param {PointerEvent} ev
     */
    onClick(ev) {
        if (!ev.target.closest(FOCUSABLE_SELECTOR)) {
            // Unselect suite when clicking outside of a suite & in the side bar
            this.uiState.selectedSuiteId = null;
            this.uiState.resultsPage = 0;
        }
    }

    /**
     * @param {KeyboardEvent & { currentTarget: HTMLInputElement }} ev
     */
    onSearchInputKeydown(ev) {
        switch (ev.key) {
            case "ArrowDown": {
                if (ev.currentTarget.selectionEnd === ev.currentTarget.value.length) {
                    const suiteElements = this.getSuiteElements();
                    suiteElements[0]?.focus();
                }
            }
        }
    }

    /**
     * @param {KeyboardEvent & { currentTarget: HTMLButtonElement }} ev
     * @param {Suite} suite
     */
    onSuiteKeydown(ev, suite) {
        /**
         * @param {number} delta
         */
        const selectElementAt = (delta) => {
            const suiteElements = this.getSuiteElements();
            const nextIndex = suiteElements.indexOf(ev.currentTarget) + delta;
            if (nextIndex < 0) {
                this.searchInputRef.el?.focus();
            } else if (nextIndex >= suiteElements.length) {
                suiteElements[0].focus();
            } else {
                suiteElements[nextIndex].focus();
            }
        };

        switch (ev.key) {
            case "ArrowDown": {
                return selectElementAt(+1);
            }
            case "ArrowLeft": {
                if (this.state.unfoldedIds.has(suite.id)) {
                    return this.toggleItem(suite, false);
                } else {
                    return selectElementAt(-1);
                }
            }
            case "ArrowRight": {
                if (this.state.unfoldedIds.has(suite.id)) {
                    return selectElementAt(+1);
                } else {
                    return this.toggleItem(suite, true);
                }
            }
            case "ArrowUp": {
                return selectElementAt(-1);
            }
            case "Enter": {
                ev.preventDefault();
                actualLocation.href = createUrlFromId(suite.id, "suite");
            }
        }
    }

    /**
     * @param {boolean} expanded
     */
    toggleExpand(expanded) {
        if (expanded) {
            this.state.unfoldedIds.clear();
        } else {
            for (const { id } of this.env.runner.suites.values()) {
                this.state.unfoldedIds.add(id);
            }
        }
    }

    /**
     * @param {Suite} suite
     * @param {boolean} [forceAdd]
     */
    toggleItem(suite, forceAdd) {
        if (this.uiState.selectedSuiteId !== suite.id) {
            this.uiState.selectedSuiteId = suite.id;
            this.uiState.resultsPage = 0;

            if (this.state.unfoldedIds.has(suite.id)) {
                return;
            }
        }

        if (forceAdd ?? !this.state.unfoldedIds.has(suite.id)) {
            this.unfoldAndSelect(suite);
        } else {
            this.state.unfoldedIds.delete(suite.id);
        }
    }

    /**
     * @param {Suite} suite
     */
    unfoldAndSelect(suite) {
        this.state.unfoldedIds.add(suite.id);

        while (suite.currentJobs.length === 1) {
            suite = suite.currentJobs[0];
            if (!(suite instanceof Suite)) {
                break;
            }
            this.state.unfoldedIds.add(suite.id);
            this.uiState.selectedSuiteId = suite.id;
            this.uiState.resultsPage = 0;
        }
    }
}
