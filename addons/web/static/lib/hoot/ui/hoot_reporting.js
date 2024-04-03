/** @odoo-module */

import { Component, onWillRender, useState, xml } from "@odoo/owl";
import { parseRegExp } from "../../hoot-dom/hoot_dom_utils";
import { Test } from "../core/test";
import { EXCLUDE_PREFIX } from "../core/url";
import { formatTime, getFuzzyScore, normalize } from "../hoot_utils";
import { HootJobButtons } from "./hoot_job_buttons";
import { HootTestPath } from "./hoot_test_path";
import { HootTestResult } from "./hoot_test_result";

/**
 * @typedef {{
 * }} HootReportingProps
 *
 * @typedef {import("../core/test").Test} Test
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Boolean, RegExp } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const sortByDurationAscending = (a, b) => a.duration - b.duration;

const sortByDurationDescending = (a, b) => b.duration - a.duration;

const COLORS = {
    failed: "text-fail",
    passed: "text-pass",
    skipped: "text-skip",
    todo: "text-todo",
};

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @extends {Component<HootReportingProps, import("../hoot").Environment>} */
export class HootReporting extends Component {
    static components = { HootJobButtons, HootTestPath, HootTestResult };

    static props = {};

    static template = xml`
        <div class="${HootReporting.name} flex-1 overflow-y-auto">
            <t t-set="resultStart" t-value="uiState.resultsPage * uiState.resultsPerPage" />
            <t t-foreach="filteredResults.slice(resultStart, resultStart + uiState.resultsPerPage)" t-as="result" t-key="result.id">
                <HootTestResult
                    open="state.openTests.includes(result.test.id)"
                    test="result.test"
                >
                    <div class="flex gap-2 overflow-hidden">
                        <HootTestPath canCopy="true" showStatus="true" test="result.test" />
                    </div>
                    <div class="flex items-center ms-1 gap-2">
                        <small
                            class="whitespace-nowrap"
                            t-attf-class="text-{{ result.test.config.skip ? 'skip' : 'muted' }}"
                        >
                            <t t-if="result.test.config.skip">
                                skipped
                            </t>
                            <t t-else="">
                                <t t-if="result.test.status === Test.ABORTED">
                                    aborted after
                                </t>
                                <t t-esc="formatTime(result.test.lastResults.duration, 'ms')" />
                            </t>
                        </small>
                        <HootJobButtons job="result.test" />
                    </div>
                </HootTestResult>
            </t>
            <t t-if="!filteredResults.length">
                <em class="text-center text-muted w-full p-4 whitespace-nowrap">
                    <t t-set="message" t-value="getEmptyMessage()" />
                    <t t-if="message">
                        <div>
                            No
                            <span
                                t-if="message.statusFilter"
                                t-att-class="message.statusFilterClassName"
                                t-esc="message.statusFilter"
                            />
                            tests found
                            <t t-if="message.filter">
                                matching
                                <strong class="text-primary" t-esc="message.filter" />
                            </t>
                            <t t-if="message.selectedSuiteName">
                                in suite
                                <strong class="text-primary" t-esc="message.selectedSuiteName" />
                            </t>.
                        </div>
                    </t>
                    <t t-else="">
                        <div class="mb-2">
                            No tests to show.
                        </div>
                        <div>
                            Click on a
                            <span class="text-primary">suite</span>
                            or toggle
                            <span class="text-primary">filters</span>
                            to see tests.
                        </div>
                    </t>
                </em>
            </t>
        </div>
    `;

    Test = Test;
    formatTime = formatTime;

    setup() {
        const { runner, ui } = this.env;

        this.config = useState(runner.config);
        this.runnerState = useState(runner.state);
        this.state = useState({
            /** @type {string[]} */
            openGroups: [],
            /** @type {string[]} */
            openTests: [],
        });
        this.uiState = useState(ui);

        const { showdetail } = this.config;

        let didShowDetail = false;
        runner.__afterPostTest((test) => {
            if (
                showdetail &&
                !(showdetail === "first-fail" && didShowDetail) &&
                [Test.FAILED, Test.ABORTED].includes(test.status)
            ) {
                didShowDetail = true;
                this.state.openTests.push(test.id);
            }
        });

        onWillRender(() => {
            this.filteredResults = this.computeFilteredResults();
            this.uiState.totalResults = this.filteredResults.length;
        });
    }

    computeFilteredResults() {
        const { selectedSuiteId, sortResults, statusFilter } = this.uiState;

        const queryFilter = this.getQueryFilter();

        const results = [];
        for (const test of this.runnerState.done) {
            let matchFilter = false;
            switch (statusFilter) {
                case "failed": {
                    matchFilter = !test.config.skip && test.results.some((r) => !r.pass);
                    break;
                }
                case "passed": {
                    matchFilter =
                        !test.config.todo && !test.config.skip && test.results.every((r) => r.pass);
                    break;
                }
                case "skipped": {
                    matchFilter = test.config.skip;
                    break;
                }
                case "todo": {
                    matchFilter = test.config.todo;
                    break;
                }
                default: {
                    matchFilter = Boolean(selectedSuiteId) || test.results.some((r) => !r.pass);
                    break;
                }
            }
            if (matchFilter && selectedSuiteId) {
                matchFilter = test.path.some((suite) => suite.id === selectedSuiteId);
            }
            if (matchFilter && queryFilter) {
                matchFilter = queryFilter(test.key);
            }
            if (!matchFilter) {
                continue;
            }
            results.push({
                duration: test.lastResults?.duration,
                status: test.status,
                id: `test#${test.id}`,
                test: test,
            });
        }

        if (!sortResults) {
            return results;
        }

        return results.sort(
            sortResults === "asc" ? sortByDurationAscending : sortByDurationDescending
        );
    }

    getEmptyMessage() {
        const { selectedSuiteId, statusFilter } = this.uiState;
        if (!statusFilter && !selectedSuiteId) {
            return null;
        }
        return {
            statusFilter,
            statusFilterClassName: COLORS[statusFilter],
            filter: this.config.filter,
            selectedSuiteName: selectedSuiteId && this.env.runner.suites.get(selectedSuiteId).name,
        };
    }

    getQueryFilter() {
        const { filter } = this.config;
        if (!filter) {
            return null;
        }
        const nFilter = parseRegExp(normalize(filter), { safe: true });
        if (nFilter instanceof RegExp) {
            return (key) => nFilter.test(key);
        }

        const isExcluding = nFilter.startsWith(EXCLUDE_PREFIX);
        const pattern = isExcluding ? nFilter.slice(EXCLUDE_PREFIX.length) : nFilter;
        return (key) => getFuzzyScore(pattern, key) > 0;
    }

    /**
     * @param {PointerEvent} ev
     * @param {string} id
     */
    toggleGroup(ev, id) {
        const index = this.state.openGroups.indexOf(id);
        if (ev.altKey) {
            if (index in this.state.openGroups) {
                this.state.openGroups = [];
            } else {
                this.state.openGroups = this.filteredResults
                    .filter((r) => r.suite)
                    .map((r) => r.suite.id);
            }
        } else {
            if (index in this.state.openGroups) {
                this.state.openGroups.splice(index, 1);
            } else {
                this.state.openGroups.push(id);
            }
        }
    }
}
