/** @odoo-module */

import { Component, onWillRender, useState, xml } from "@odoo/owl";
import { Test } from "../core/test";
import { refresh } from "../core/url";
import { formatTime } from "../hoot_utils";
import { HootTestPath } from "./hoot_test_path";

/**
 * @typedef {import("../core/expect").Assertion} Assertion
 *
 * @typedef {{
 *  test: Test;
 * }} HootDebugToolBarProps
 *
 * @typedef {import("../core/expect").TestResult} TestResult
 */

/** @extends {Component<HootDebugToolBarProps, import("../hoot").Environment>} */
export class HootDebugToolBar extends Component {
    static components = { HootTestPath };

    static props = {
        test: Test,
    };

    static template = xml`
        <div class="${HootDebugToolBar.name} absolute start-0 bottom-0 p-4 z-4 max-w-full">
            <details class="flex flex-col overflow-hidden rounded shadow bg-gray-200 dark:bg-gray-800" open="">
                <summary class="flex items-center gap-1 px-2 bg-gray-300 dark:bg-gray-700">
                    <i class="fa fa-bug text-skip" />
                    <HootTestPath full="true" test="props.test" />
                </summary>
                <div class="flex gap-2 px-2">
                    <div class="flex gap-px rounded my-1 overflow-hidden min-w-fit">
                        <button class="bg-btn px-2 py-1" title="Exit debug mode (Ctrl + Esc)" t-on-click="exitDebugMode">
                            <i class="fa fa-sign-out" />
                        </button>
                        <t t-if="done">
                            <button class="bg-btn px-2 py-1 animate-slide-left" title="Restart test (F5)" t-on-click="restart">
                                <i class="fa fa-refresh" />
                            </button>
                        </t>
                    </div>
                    <div class="flex items-center gap-1 truncate">
                        status:
                        <strong
                            t-attf-class="text-{{ info.className }}"
                            t-esc="info.status"
                        />
                        <span class="text-muted">-</span>
                        assertions:
                        <span class="flex gap-1 text-pass">
                            <strong t-esc="info.passed" />
                            <span class="hidden sm:inline">passed</span>
                        </span>
                        <t t-if="info.failed">
                            <span class="text-muted">/</span>
                            <span class="flex gap-1 text-fail">
                                <strong t-esc="info.failed" />
                                <span class="hidden sm:inline">failed</span>
                            </span>
                        </t>
                        <span class="text-muted">-</span>
                        time:
                        <span
                            class="text-primary"
                            t-esc="formatTime(props.test.lastResults?.duration, 'ms')"
                        />
                    </div>
                </div>
            </details>
        </div>
    `;

    formatTime = formatTime;

    get done() {
        return Boolean(this.runnerState.done.length); // subscribe to test being added as done
    }

    setup() {
        this.runnerState = useState(this.env.runner.state);

        onWillRender(() => {
            this.info = this.getInfo();
        });
    }

    exitDebugMode() {
        const { runner } = this.env;
        runner.config.debugTest = false;
        runner.stop();
    }

    getInfo() {
        const [status, className] = this.getStatus();
        const [assertPassed, assertFailed] = this.groupAssertions(
            this.props.test.lastResults?.assertions
        );
        return {
            className,
            status,
            passed: assertPassed,
            failed: assertFailed,
        };
    }

    getStatus() {
        if (this.props.test.lastResults) {
            switch (this.props.test.status) {
                case Test.PASSED:
                    return ["passed", "pass"];
                case Test.FAILED:
                    return ["failed", "fail"];
                case Test.ABORTED:
                    return ["aborted", "abort"];
            }
        }
        return ["running", "skip"];
    }

    /**
     * @param {Assertion[]} [assertions]
     */
    groupAssertions(assertions) {
        let passed = 0;
        let failed = 0;
        for (const assertion of assertions || []) {
            if (assertion.pass) {
                passed++;
            } else {
                failed++;
            }
        }
        return [passed, failed];
    }

    restart() {
        refresh();
    }
}
