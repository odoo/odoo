/** @odoo-module */

import { Component, markRaw, onWillRender, useState, xml } from "@odoo/owl";
import { parseRegExp } from "../../hoot-dom/hoot_dom_utils";
import { Test } from "../core/test";
import { EXCLUDE_PREFIX, subscribeToURLParams } from "../core/url";
import { batch, formatTime, getFuzzyScore, normalize } from "../hoot_utils";
import { HootStatusPanel } from "./hoot_status_panel";
import { HootTestResult } from "./hoot_test_result";

/**
 * @typedef {{}} HootReportingProps
 *
 * @typedef {import("../core/test").Test} Test
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Math } = globalThis;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @extends {Component<HootReportingProps, import("../hoot").Environment>} */
export class HootReporting extends Component {
    static components = { HootStatusPanel, HootTestResult };

    static props = {};

    static template = xml`
        <div class="flex flex-col overflow-y-auto">
            <HootStatusPanel
                filter="state.filter"
                filterResults.bind="filterResults"
                grouped="state.grouped"
                groupResults.bind="groupResults"
                sorted="state.sorted"
                sortResults.bind="sortResults"
            />
            <div class="overflow-y-auto">
                <t t-foreach="filteredResults" t-as="result" t-key="result.id">
                    <t t-if="result.suite">
                        <button
                            type="button"
                            class="whitespace-nowrap flex items-center justify-between gap-1 w-full px-2 border-b border-gray-300 dark:border-gray-600"
                            t-on-click="(ev) => this.toggleGroup(ev, result.suite.id)"
                        >
                            <span class="flex items-center">
                                <i
                                    class="fa fa-chevron-right flex justify-center transition"
                                    t-att-class="{ 'rotate-90': state.openGroups.includes(result.suite.id) }"
                                    style="font-size: 12px"
                                />
                                <span class="flex items-center overflow-hidden">
                                    <t t-foreach="result.suite.path" t-as="suite" t-key="suite.id">
                                        <strong
                                            class="whitespace-nowrap p-1"
                                            t-att-class="{
                                                'hidden md:inline text-muted': !suite_last,
                                                'text-primary': suite_last,
                                                'text-skip': suite.config.skip,
                                            }"
                                            t-esc="suite.name"
                                        />
                                        <t t-if="!suite_last">
                                            <span class="select-none hidden md:inline" t-att-class="{ 'text-skip': suite.config.skip }">/</span>
                                        </t>
                                        <t t-else="">
                                            (<strong class="text-primary" t-esc="result.suite.currentJobs.length" />)
                                        </t>
                                    </t>
                                </span>
                            </span>
                            <small
                                class="whitespace-nowrap"
                                t-attf-class="text-{{ result.suite.config.skip ? 'skip' : 'muted' }}"
                                t-esc="formatTime(result.duration, 'ms')"
                            />
                        </button>
                    </t>
                    <t t-elif="!state.grouped or state.openGroups.includes(result.test.parent.id)">
                        <HootTestResult test="result.test" open="state.openTests.includes(result.test.id)" />
                    </t>
                </t>
            </div>
        </div>
    `;

    formatTime = formatTime;

    setup() {
        const { runner } = this.env;

        this.urlParams = subscribeToURLParams("showskipped", "showpassed");

        this.state = useState({
            filter: null,
            grouped: false,
            /** @type {string[]} */
            openGroups: [],
            /** @type {string[]} */
            openTests: [],
            sorted: false,
            /** @type {Record<string, Test>} */
            tests: {},
        });

        const [addTest] = batch((test) => {
            this.state.tests[test.id] = markRaw(test);
            if (
                showdetail &&
                !(showdetail === "first-fail" && didShowDetail) &&
                [Test.FAILED, Test.ABORTED].includes(test.status)
            ) {
                didShowDetail = true;
                this.state.openTests.push(test.id);
            }
        }, 100);

        let didShowDetail = false;
        const { showdetail } = this.env.runner.config;
        runner.afterTestDone(addTest);
        runner.onTestSkipped(addTest);

        onWillRender(() => {
            this.filteredResults = this.getFilteredResults();
        });
    }

    filterResults(filter) {
        this.state.filter = this.state.filter === filter ? null : filter;
    }

    getQueryFilter() {
        const { filter } = this.urlParams;
        if (!filter) {
            return null;
        }
        const nFilter = parseRegExp(normalize(this.urlParams.filter));
        if (nFilter instanceof RegExp) {
            return (key) => nFilter.test(key);
        }

        const isExcluding = nFilter.startsWith(EXCLUDE_PREFIX);
        const pattern = isExcluding ? nFilter.slice(EXCLUDE_PREFIX.length) : nFilter;
        return (key) => getFuzzyScore(pattern, key) > 0;
    }

    getFilteredResults() {
        const makeResult = ({ suite, test }) =>
            suite
                ? {
                      suite: suite,
                      duration: 0,
                      id: `suite#${suite.id}`,
                  }
                : {
                      test: test,
                      duration: test.lastResults?.duration,
                      id: `test#${test.id}`,
                  };

        const { showskipped, showpassed } = this.env.runner.config;
        const { filter, grouped, sorted, tests } = this.state;

        const queryFilter = this.getQueryFilter();

        const groups = grouped ? {} : [];
        for (const test of Object.values(tests)) {
            let matchFilter = false;
            switch (filter) {
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
                    if (!showskipped && test.config.skip) {
                        matchFilter = false;
                    } else if (
                        !showpassed &&
                        test.results.length &&
                        test.results.every((r) => r.pass)
                    ) {
                        matchFilter = false;
                    } else {
                        matchFilter = true;
                    }
                    break;
                }
            }
            if (matchFilter && queryFilter) {
                matchFilter = queryFilter(test.key);
            }
            if (!matchFilter) {
                continue;
            }
            if (grouped) {
                const suite = test.parent;
                const key = suite.id;
                if (!groups[key]) {
                    groups[key] = [makeResult({ suite })];
                }
                const result = makeResult({ test });
                groups[key][0].duration += result.duration;
                groups[key].push(result);
            } else {
                groups.push(makeResult({ test }));
            }
        }

        if (sorted) {
            const predicate =
                sorted === "asc"
                    ? (a, b) => a.duration - b.duration
                    : (a, b) => b.duration - a.duration;
            if (!grouped) {
                // Sorted, not grouped
                return groups.sort(predicate);
            }

            // Sorted & grouped
            const groupValues = Object.values(groups);
            for (const group of groupValues) {
                const suite = group.shift();
                group.sort(predicate);
                group.unshift(suite);
            }
            const groupPredicate =
                sorted === "asc"
                    ? (a, b) => a[0].duration - b[0].duration
                    : (a, b) => b[0].duration - a[0].duration;
            return groupValues.sort(groupPredicate).flat();
        }

        if (grouped) {
            // Grouped, not sorted
            return Object.values(groups).flat();
        }

        // Not grouped, not sorted
        return groups;
    }

    groupResults() {
        this.state.grouped = !this.state.grouped;
    }

    sortResults() {
        if (!this.state.sorted) {
            this.state.sorted = "desc";
        } else if (this.state.sorted === "desc") {
            this.state.sorted = "asc";
        } else {
            this.state.sorted = false;
        }
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
