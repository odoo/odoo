/** @odoo-module */

import { Component, onWillRender, useState, xml } from "@odoo/owl";
import { parseRegExp } from "../../hoot-dom/hoot_dom_utils";
import { Test } from "../core/test";
import { EXCLUDE_PREFIX, subscribeToURLParams } from "../core/url";
import { batch, formatTime, getFuzzyScore, normalize } from "../hoot_utils";
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
            <t t-foreach="filteredResults" t-as="result" t-key="result.id">
                <HootTestResult
                    open="state.openTests.includes(result.test.id)"
                    test="result.test"
                >
                    <div class="flex gap-2 overflow-hidden">
                        <HootTestPath canCopy="true" test="result.test" />
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
                <em class="flex justify-center text-muted w-full gap-1 p-4">
                    <t t-foreach="getEmptyMessage()" t-as="messagePart" t-key="messagePart_index">
                        <t t-if="typeof messagePart === 'string'">
                            <t t-esc="messagePart" />
                        </t>
                        <t t-else="">
                            <t
                                t-tag="messagePart.tagName or 'span'"
                                t-att-class="messagePart.className"
                                t-esc="messagePart.content or ''"
                            />
                        </t>
                    </t>
                </em>
            </t>
        </div>
    `;

    Test = Test;
    formatTime = formatTime;

    setup() {
        const { runner, ui } = this.env;
        const { showdetail } = runner.config;

        this.urlParams = subscribeToURLParams("filter");

        this.state = useState({
            /** @type {string[]} */
            openGroups: [],
            /** @type {string[]} */
            openTests: [],
            /** @type {Record<string, Test>} */
            tests: {},
        });
        this.uiState = useState(ui);

        const [addTest] = batch((test) => {
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
        runner.beforeAll(() => {
            for (const id of runner.tests.keys()) {
                this.state.tests[id] = null;
            }
        });
        runner.afterTestDone(addTest);
        runner.onTestSkipped(addTest);

        onWillRender(() => {
            this.filteredResults = this.getFilteredResults();
        });
    }

    getEmptyMessage() {
        const { suites } = this.env.runner;
        const { selectedSuiteId, statusFilter } = this.uiState;
        const { filter } = this.urlParams;

        if (!statusFilter && !selectedSuiteId) {
            return [
                "No tests to show. Click on a",
                {
                    tagName: "strong",
                    className: "text-primary",
                    content: "suite",
                },
                "or toggle",
                {
                    tagName: "strong",
                    className: "text-primary",
                    content: "filters",
                },
                "to see tests.",
            ];
        }

        /**
         * @param {string} text
         */
        const addText = (text) => {
            const lastIndex = message.length - 1;
            if (typeof message[lastIndex] === "string") {
                message[lastIndex] += text;
            } else {
                message.push(text.trim());
            }
        };

        const message = [];
        if (statusFilter) {
            message.push(
                "No",
                {
                    className: COLORS[statusFilter],
                    content: statusFilter,
                },
                "tests found"
            );
        } else {
            message.push("No tests found");
        }
        if (filter) {
            addText(" matching");
            message.push({
                tagName: "strong",
                className: "text-primary",
                content: `"${filter}"`,
            });
        }
        if (selectedSuiteId) {
            addText(" in suite");
            message.push({
                tagName: "strong",
                className: "text-primary",
                content: suites.get(selectedSuiteId).name,
            });
        }

        addText(".");

        return message;
    }

    getQueryFilter() {
        const { filter } = this.urlParams;
        if (!filter) {
            return null;
        }
        const nFilter = parseRegExp(normalize(filter));
        if (nFilter instanceof RegExp) {
            return (key) => nFilter.test(key);
        }

        const isExcluding = nFilter.startsWith(EXCLUDE_PREFIX);
        const pattern = isExcluding ? nFilter.slice(EXCLUDE_PREFIX.length) : nFilter;
        return (key) => getFuzzyScore(pattern, key) > 0;
    }

    getFilteredResults() {
        const makeResult = (test) => ({
            duration: test.lastResults?.duration,
            status: test.status,
            id: `test#${test.id}`,
            test: test,
        });

        const { selectedSuiteId, sortResults, statusFilter } = this.uiState;

        const queryFilter = this.getQueryFilter();

        const results = [];
        for (const test of Object.values(this.state.tests)) {
            if (!test) {
                continue; // Test not yet registered
            }
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
            results.push(makeResult(test));
        }

        let predicate;
        if (sortResults) {
            predicate =
                sortResults === "asc"
                    ? (a, b) => a.duration - b.duration
                    : (a, b) => b.duration - a.duration;
        } else {
            predicate = (a, b) => b.status - a.status;
        }

        return results.sort(predicate);
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
