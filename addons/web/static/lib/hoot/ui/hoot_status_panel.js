/** @odoo-module */

import { Component, onWillRender, useEffect, useRef, useState, xml } from "@odoo/owl";
import { Test } from "../core/test";
import { formatTime } from "../hoot_utils";
import { getTitle, setTitle } from "../mock/window";
import { getColors } from "./hoot_colors";
import { HootTestPath } from "./hoot_test_path";

/**
 * @typedef {{
 * }} HootStatusPanelProps
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Object: { values: $values },
    Math: { ceil: $ceil, floor: $floor, max: $max, min: $min, random: $random },
    clearInterval,
    document,
    performance,
    setInterval,
} = globalThis;
/** @type {Performance["now"]} */
const $now = performance.now.bind(performance);

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {number} min
 * @param {number} max
 */
const randInt = (min, max) => $floor($random() * (max - min + 1)) + min;

/**
 * @param {string} content
 */
const spawnIncentive = (content) => {
    const incentive = document.createElement("div");
    const params = [
        `--_content: '${content}'`,
        `--_fly-duration: ${randInt(2_000, 3_000)}`,
        `--_size: ${randInt(32, 48)}`,
        `--_wiggle-duration: ${randInt(800, 2_000)}`,
        `--_wiggle-range: ${randInt(5, 30)}`,
        `--_x: ${randInt(0, 100)}`,
        `--_y: ${randInt(100, 150)}`,
    ];
    incentive.setAttribute("class", `incentive fixed`);
    incentive.setAttribute("style", params.join(";"));

    /** @param {AnimationEvent} ev */
    const onEnd = (ev) => ev.animationName === "animation-incentive-travel" && incentive.remove();
    incentive.addEventListener("animationend", onEnd);
    incentive.addEventListener("animationcancel", onEnd);

    document.querySelector("hoot-container").shadowRoot.appendChild(incentive);
};

/**
 * @param {boolean} failed
 */
const updateTitle = (failed) => {
    const toAdd = failed ? TITLE_PREFIX.fail : TITLE_PREFIX.pass;
    let title = getTitle();
    if (title.startsWith(toAdd)) {
        return;
    }
    for (const prefix of $values(TITLE_PREFIX)) {
        if (title.startsWith(prefix)) {
            title = title.slice(prefix.length);
            break;
        }
    }
    setTitle(`${toAdd} ${title}`);
};

const TITLE_PREFIX = {
    fail: "✖",
    pass: "✔",
};

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @extends {Component<HootStatusPanelProps, import("../hoot").Environment>} */
export class HootStatusPanel extends Component {
    static components = { HootTestPath };

    static props = {};

    static template = xml`
        <div class="${HootStatusPanel.name} flex items-center justify-between gap-3 px-3 py-1 bg-gray-300 dark:bg-gray-700" t-att-class="state.className">
            <div class="flex items-center gap-2 overflow-hidden">
                <t t-if="runnerState.status === 'ready'">
                    Ready
                </t>
                <t t-elif="runnerState.status === 'running'">
                    <i t-if="state.debug" class="text-skip fa fa-bug" title="Debugging" />
                    <div
                        t-else=""
                        class="animate-spin shrink-0 grow-0 w-4 h-4 border-2 border-pass border-t-transparent rounded-full"
                        role="status"
                        title="Running"
                    />
                </t>
                <t t-else="">
                    <span class="hidden md:block">
                        <strong class="text-primary" t-esc="runnerReporting.tests" />
                        tests completed
                        (total time: <strong class="text-primary" t-esc="env.runner.totalTime" />
                        <t t-if="env.runner.aborted">, run aborted by user</t>)
                    </span>
                    <span class="md:hidden flex items-center gap-1">
                        <i class="fa fa-clock-o" />
                        <strong class="text-primary" t-esc="env.runner.totalTime" />
                    </span>
                </t>
                <t t-if="runnerState.currentTest">
                    <HootTestPath test="runnerState.currentTest" />
                </t>
                <t t-if="state.timer">
                    <span class="text-skip" t-esc="formatTime(state.timer, 's')" />
                </t>
            </div>
            <div class="flex items-center gap-1">
                <t t-if="runnerReporting.passed">
                    <t t-set="color" t-value="!uiState.statusFilter or uiState.statusFilter === 'passed' ? 'pass' : 'muted'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click="() => this.filterResults('passed')"
                        t-attf-title="Show {{ runnerReporting.passed }} passed tests"
                    >
                        <i class="fa fa-check-circle" />
                        <t t-esc="runnerReporting.passed" />
                    </button>
                </t>
                <t t-if="runnerReporting.failed">
                    <t t-set="color" t-value="!uiState.statusFilter or uiState.statusFilter === 'failed' ? 'fail' : 'muted'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click="() => this.filterResults('failed')"
                        t-attf-title="Show {{ runnerReporting.failed }} failed tests"
                    >
                        <i class="fa fa-times-circle" />
                        <t t-esc="runnerReporting.failed" />
                    </button>
                </t>
                <t t-if="runnerReporting.skipped">
                    <t t-set="color" t-value="!uiState.statusFilter or uiState.statusFilter === 'skipped' ? 'skip' : 'muted'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click="() => this.filterResults('skipped')"
                        t-attf-title="Show {{ runnerReporting.skipped }} skipped tests"
                    >
                        <i class="fa fa-pause-circle" />
                        <t t-esc="runnerReporting.skipped" />
                    </button>
                </t>
                <t t-if="runnerReporting.todo">
                    <t t-set="color" t-value="!uiState.statusFilter or uiState.statusFilter === 'todo' ? 'todo' : 'muted'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click="() => this.filterResults('todo')"
                        t-attf-title="Show {{ runnerReporting.todo }} tests to do"
                    >
                        <i class="fa fa-exclamation-circle" />
                        <t t-esc="runnerReporting.todo" />
                    </button>
                </t>
                <button
                    class="p-1 transition-colors"
                    t-att-class="{ 'text-primary': uiState.sortResults }"
                    title="Sort by duration"
                    t-on-click="sortResults"
                >
                    <i t-attf-class="fa fa-sort-numeric-{{ uiState.sortResults or 'desc' }} transition" />
                </button>
                <t t-if="uiState.totalResults gt uiState.resultsPerPage">
                    <t t-set="lastPage" t-value="getLastPage()" />
                    <div class="flex gap-1 animate-slide-left">
                        <button
                            class="px-1 transition-color"
                            title="Previous page"
                            t-att-disabled="uiState.resultsPage === 0"
                            t-on-click="previousPage"
                        >
                            <i class="fa fa-chevron-left" />
                        </button>
                        <strong class="text-primary" t-esc="uiState.resultsPage + 1" />
                        <span class="text-muted">/</span>
                        <t t-esc="lastPage + 1" />
                        <button
                            class="px-1 transition-color"
                            title="Next page"
                            t-att-disabled="uiState.resultsPage === lastPage"
                            t-on-click="nextPage"
                        >
                            <i class="fa fa-chevron-right" />
                        </button>
                    </div>
                </t>
            </div>
        </div>
        <canvas t-ref="progress-canvas" class="flex h-1 w-full" />
    `;

    formatTime = formatTime;

    setup() {
        const startTimer = () => {
            stopTimer();

            currentTestStart = $now();
            intervalId = setInterval(() => {
                this.state.timer = $floor($now() - currentTestStart);
            }, 1000);
        };

        const stopTimer = () => {
            if (intervalId) {
                clearInterval(intervalId);
                intervalId = 0;
            }

            this.state.timer = 0;
        };

        const { runner, ui } = this.env;
        this.canvasRef = useRef("progress-canvas");
        this.runnerReporting = useState(runner.reporting);
        this.runnerState = useState(runner.state);
        this.state = useState({
            className: "",
            timer: null,
        });
        this.uiState = useState(ui);
        this.progressBarIndex = 0;

        let currentTestStart;
        let intervalId = 0;

        runner.beforeAll(() => {
            this.state.debug = runner.debug;
        });

        runner.afterAll(() => {
            if (!runner.config.headless) {
                stopTimer();
            }
            updateTitle(this.runnerReporting.failed > 0);

            if (runner.config.fun) {
                for (let i = 0; i < this.runnerReporting.failed; i++) {
                    spawnIncentive("😭");
                }
                for (let i = 0; i < this.runnerReporting.passed; i++) {
                    spawnIncentive("🦉");
                }
            }
        });

        if (!runner.config.headless) {
            runner.beforeEach(startTimer);
            runner.afterPostTest(stopTimer);
        }

        useEffect(
            (el) => {
                if (el) {
                    [el.width, el.height] = [el.clientWidth, el.clientHeight];
                    el.getContext("2d").clearRect(0, 0, el.width, el.height);
                }
            },
            () => [this.canvasRef.el]
        );

        onWillRender(() => this.updateProgressBar());
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

    getLastPage() {
        const { resultsPerPage, totalResults } = this.uiState;
        return $max($floor((totalResults - 1) / resultsPerPage), 0);
    }

    nextPage() {
        this.uiState.resultsPage = $min(this.uiState.resultsPage + 1, this.getLastPage());
    }

    previousPage() {
        this.uiState.resultsPage = $max(this.uiState.resultsPage - 1, 0);
    }

    sortResults() {
        this.uiState.resultsPage = 0;
        if (!this.uiState.sortResults) {
            this.uiState.sortResults = "desc";
        } else if (this.uiState.sortResults === "desc") {
            this.uiState.sortResults = "asc";
        } else {
            this.uiState.sortResults = false;
        }
    }

    updateProgressBar() {
        const canvas = this.canvasRef.el;
        if (!canvas) {
            return;
        }

        const ctx = canvas.getContext("2d");
        const { width, height } = canvas;
        const { done, tests } = this.runnerState;
        const doneList = [...done];
        const cellSize = width / tests.length;
        const colors = getColors();

        while (this.progressBarIndex < done.size) {
            const test = doneList[this.progressBarIndex];
            const x = $floor(this.progressBarIndex * cellSize);
            switch (test.status) {
                case Test.ABORTED:
                    ctx.fillStyle = colors.abort;
                    break;
                case Test.FAILED:
                    ctx.fillStyle = colors.fail;
                    break;
                case Test.PASSED:
                    ctx.fillStyle = test.config.todo ? colors.todo : colors.pass;
                    break;
                case Test.SKIPPED:
                    ctx.fillStyle = colors.skip;
                    break;
            }
            ctx.fillRect(x, 0, $ceil(cellSize), height);
            this.progressBarIndex++;
        }
    }
}
