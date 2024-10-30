/** @odoo-module */

import { Component, onWillRender, useState, xml } from "@odoo/owl";
import { parseRegExp } from "../../hoot-dom/hoot_dom_utils";
import { Test } from "../core/test";
import { EXCLUDE_PREFIX } from "../core/url";
import { formatTime, getFuzzyScore, normalize } from "../hoot_utils";
import { HootLogCounters } from "./hoot_log_counters";
import { HootJobButtons } from "./hoot_job_buttons";
import { HootTechnicalValue } from "./hoot_technical_value";
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

/**
 * @param {keyof import("../core/runner").Runner["state"]} varName
 * @param {string} colorClassName
 */
const issueTemplate = (varName, colorClassName) => /* xml */ `
    <t t-foreach="runnerState['${varName}']" t-as="key" t-key="key">
        <t t-set="issue" t-value="runnerState['${varName}'][key]" />
        <div
            class="flex flex-col justify-center px-3 py-2 gap-2 border-muted border-b text-${colorClassName} bg-${colorClassName}-900"
            t-att-title="issue.message"
        >
            <h3 class="flex items-center gap-1 whitespace-nowrap">
                <span class="min-w-3 min-h-3 rounded-full bg-${colorClassName}" />
                Global <t t-esc="issue.name" />
                <span t-if="issue.count > 1">
                    (x<t t-esc="issue.count" />)
                </span>:
                <small class="ms-auto text-muted whitespace-nowrap italic font-normal">
                    stack trace available in the console
                </small>
            </h3>
            <ul>
                <t t-foreach="issue.message.split('\\n')" t-as="messagePart" t-key="messagePart_index">
                    <li class="truncate" t-esc="messagePart" />
                </t>
            </ul>
        </div>
    </t>`;

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
    static components = {
        HootLogCounters,
        HootJobButtons,
        HootTechnicalValue,
        HootTestPath,
        HootTestResult,
    };

    static props = {};

    static template = xml`
        <div class="${HootReporting.name} flex-1 overflow-y-auto">
            <!-- Errors -->
            ${issueTemplate("globalErrors", "fail")}

            <!-- Warnings -->
            ${issueTemplate("globalWarnings", "abort")}

            <!-- Test results -->
            <t t-set="resultStart" t-value="uiState.resultsPage * uiState.resultsPerPage" />
            <t t-foreach="filteredResults.slice(resultStart, resultStart + uiState.resultsPerPage)" t-as="result" t-key="result.id">
                <HootTestResult
                    open="state.openTests.includes(result.test.id)"
                    test="result.test"
                >
                    <div class="flex items-center gap-2 overflow-hidden">
                        <HootTestPath canCopy="true" showStatus="true" test="result.test" />
                        <HootLogCounters logs="result.test.logs" />
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

            <!-- "No test" panel -->
            <t t-if="!filteredResults.length">
                <div class="flex items-center justify-center h-full">
                    <t t-set="message" t-value="getEmptyMessage()" />
                    <t t-if="message">
                        <em class="p-5 rounded bg-gray-200 dark:bg-gray-800 whitespace-nowrap text-muted">
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
                        </em>
                    </t>
                    <t t-else="">
                        <div class="flex flex-col gap-3 p-5 rounded bg-gray-200 dark:bg-gray-800">
                            <h3 class="border-b border-muted pb-1">
                                <strong class="text-primary" t-esc="runnerReporting.tests" />
                                /
                                <span class="text-primary" t-esc="runnerState.tests.length" />
                                tests completed
                            </h3>
                            <ul class="flex flex-col gap-2">
                                <t t-if="runnerReporting.passed">
                                    <li class="flex gap-1">
                                        <button
                                            class="flex items-center gap-1 text-pass"
                                            t-on-click.stop="() => this.filterResults('passed')"
                                        >
                                            <i class="fa fa-check-circle" />
                                            <strong t-esc="runnerReporting.passed" />
                                        </button>
                                        tests passed
                                    </li>
                                </t>
                                <t t-if="runnerReporting.failed">
                                    <li class="flex gap-1">
                                        <button
                                            class="flex items-center gap-1 text-fail"
                                            t-on-click.stop="() => this.filterResults('failed')"
                                        >
                                            <i class="fa fa-times-circle" />
                                            <strong t-esc="runnerReporting.failed" />
                                        </button>
                                        tests failed
                                    </li>
                                </t>
                                <t t-if="runnerReporting.skipped">
                                    <li class="flex gap-1">
                                        <button
                                            class="flex items-center gap-1 text-skip"
                                            t-on-click.stop="() => this.filterResults('skipped')"
                                        >
                                            <i class="fa fa-pause-circle" />
                                            <strong t-esc="runnerReporting.skipped" />
                                        </button>
                                        tests skipped
                                    </li>
                                </t>
                                <t t-if="runnerReporting.todo">
                                    <li class="flex gap-1">
                                        <button
                                            class="flex items-center gap-1 text-todo"
                                            t-on-click.stop="() => this.filterResults('todo')"
                                        >
                                            <i class="fa fa-exclamation-circle" />
                                            <strong t-esc="runnerReporting.todo" />
                                        </button>
                                        tests to do
                                    </li>
                                </t>
                            </ul>
                        </div>
                    </t>
                </div>
            </t>
        </div>
    `;

    Test = Test;
    formatTime = formatTime;

    setup() {
        const { runner, ui } = this.env;

        this.config = useState(runner.config);
        this.runnerReporting = useState(runner.reporting);
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
        runner.afterPostTest((test) => {
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

    /**
     * @param {typeof this.uiState.statusFilter} status
     */
    filterResults(status) {
        this.uiState.resultsPage = 0;
        if (this.uiState.statusFilter === status) {
            this.uiState.statusFilter = null;
        } else {
            this.uiState.statusFilter = status;
        }
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
