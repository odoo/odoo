/** @odoo-module */

import { Component, onWillRender, useState, xml } from "@odoo/owl";
import { Test } from "../core/test";
import { subscribeToURLParams } from "../core/url";
import { batch } from "../hoot_utils";
import { HootStatusPanel } from "./hoot_status_panel";
import { HootTestResult } from "./hoot_test_result";

/**
 * @typedef {{}} HootReportingProps
 *
 * @typedef {import("../core/test").Test} Test
 */

/** @extends Component<HootReportingProps, import("../hoot").Environment> */
export class HootReporting extends Component {
    static components = { HootStatusPanel, HootTestResult };

    static props = {};

    static template = xml`
        <div class="hoot-reporting d-flex flex-column">
            <HootStatusPanel
                filter="state.filter"
                filterResults.bind="filterResults"
                grouped="state.grouped"
                groupResults.bind="groupResults"
                sorted="state.sorted"
                sortResults.bind="sortResults"
            />
            <div class="hoot-results">
                <t t-foreach="filteredResults" t-as="result" t-key="result.id">
                    <t t-if="result.suite">
                        <button
                            type="button"
                            class="hoot-result text-nowrap d-flex align-items-center gap-1 w-100 py-1 px-2"
                            t-on-click="(ev) => this.toggleGroup(ev, result.suite.id)"
                        >
                            <i
                                t-attf-class="fa fa-chevron-{{ state.openGroups.includes(result.suite.id) ? 'down' : 'right' }} d-flex justify-content-center"
                                style="min-width: 16px; font-size: 12px;"
                            />
                            <h5 class="hoot-text-primary text-truncate m-0" t-esc="result.suite.fullName" />
                            <span class="d-none d-md-inline">
                                (total tests: <strong class="hoot-text-primary" t-esc="result.suite.currentJobs.length" />)
                            </span>
                        </button>
                    </t>
                    <t t-elif="!state.grouped or state.openGroups.includes(result.test.parent.id)">
                        <HootTestResult test="result.test" open="state.openTests.includes(result.test.id)" />
                    </t>
                </t>
            </div>
        </div>
    `;

    setup() {
        const { runner } = this.env;

        subscribeToURLParams("showskipped", "showpassed");

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

        const addTest = batch((test) => {
            this.state.tests[test.id] = test;
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

    getFilteredResults() {
        const makeResult = ({ suite, test }) =>
            suite ? { suite, id: `suite#${suite.id}` } : { test, id: `test#${test.id}` };

        const { showskipped, showpassed } = this.env.runner.config;
        const { filter, grouped, sorted, tests } = this.state;

        const groups = grouped || sorted ? {} : [];
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
            if (!matchFilter) {
                continue;
            }

            if (sorted) {
                const key = Math.round(test.lastResults?.duration || 0);
                if (!groups[key]) {
                    groups[key] = [];
                }
                groups[key].push(makeResult({ test }));
            } else if (grouped) {
                const suite = test.parent;
                const key = suite.id;
                if (!groups[key]) {
                    groups[key] = [makeResult({ suite })];
                }
                groups[key].push(makeResult({ test }));
            } else {
                groups.push(makeResult({ test }));
            }
        }

        if (sorted) {
            const values = Object.values(groups).flat();
            return sorted === "asc" ? values : values.reverse();
        } else if (grouped) {
            return Object.values(groups).flat();
        } else {
            return groups;
        }
    }

    groupResults() {
        this.state.sorted = false;
        this.state.grouped = !this.state.grouped;
    }

    sortResults() {
        this.state.grouped = false;
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
