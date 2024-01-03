/** @odoo-module */

import { Component, onWillRender, useEffect, useRef, useState, xml } from "@odoo/owl";
import { batch, formatTime } from "../hoot_utils";
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

const { Object, Math, clearInterval, document, performance, setInterval } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {number} min
 * @param {number} max
 */
const randInt = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;

/**
 * @param {HTMLElement} target
 * @param {string} content
 */
const spawnIncentive = (target, content) => {
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

    target.appendChild(incentive);
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
    for (const prefix of Object.values(TITLE_PREFIX)) {
        if (title.startsWith(prefix)) {
            title = title.slice(prefix.length);
            break;
        }
    }
    setTitle(`${toAdd} ${title}`);
};

const COLORS_BY_ID = {
    0: "pass",
    1: "fail",
    2: "skip",
    3: "todo",
};
const COLORS_BY_NAME = {
    pass: 0,
    fail: 1,
    skip: 2,
    todo: 3,
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
                        class="animate-spin w-4 h-4 border-2 border-pass border-t-transparent rounded-full"
                        role="status"
                        title="Running"
                    >
                        <span class="visually-hidden">Running</span>
                    </div>
                </t>
                <t t-else="">
                    <span class="hidden md:block">
                        <strong class="text-primary" t-esc="runnerReporting.tests" />
                        tests completed
                        (<strong class="text-primary" t-esc="runnerReporting.assertions" /> assertions,
                        total time: <strong class="text-primary" t-esc="env.runner.totalTime" />)
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
            <div class="flex gap-1">
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
                    <i
                        class="fa fa-filter transition"
                        t-att-class="{ 'rotate-180': uiState.sortResults === 'asc' }"
                    />
                </button>
            </div>
        </div>
        <canvas t-ref="progress-canvas" class="flex h-1 w-full" />
    `;

    formatTime = formatTime;

    setup() {
        const [addResult, flushResults] = batch((config, lastResults) => {
            if (!lastResults.pass) {
                this.results.push(COLORS_BY_NAME.fail);
            } else if (config.todo) {
                this.results.push(COLORS_BY_NAME.todo);
            } else {
                this.results.push(COLORS_BY_NAME.pass);
            }
        });

        const startTimer = () => {
            stopTimer();

            currentTestStart = performance.now();
            intervalId = setInterval(() => {
                this.state.timer = Math.floor(performance.now() - currentTestStart);
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
        let currentTestStart;
        this.canvasRef = useRef("progress-canvas");
        this.runnerReporting = useState(runner.reporting);
        this.runnerState = useState(runner.state);
        this.state = useState({
            className: "",
            timer: null,
        });
        this.uiState = useState(ui);
        /** @type {number[]} */
        this.results = [];

        let intervalId = 0;

        runner.beforeAll(() => {
            this.results = [];
            this.state.debug = runner.debug;
        });

        runner.afterAll(() => {
            if (!runner.config.headless) {
                stopTimer();
            }
            flushResults();

            updateTitle(this.runnerReporting.failed > 0);

            if (runner.config.fun) {
                const container = this.canvasRef.el.offsetParent;
                for (let i = 0; i < this.runnerReporting.failed; i++) {
                    spawnIncentive(container, "😭");
                }
                for (let i = 0; i < this.runnerReporting.passed; i++) {
                    spawnIncentive(container, "🦉");
                }
            }
        });

        if (!runner.config.headless) {
            runner.beforeEach(startTimer);
            runner.afterEach(stopTimer);
        }

        runner.afterTestDone((test) => {
            addResult(test.config, test.lastResults);
        });

        runner.onTestSkipped(() => {
            this.results.push(COLORS_BY_NAME.skip);
        });

        useEffect(
            (el) => {
                if (el) {
                    [el.width, el.height] = [el.clientWidth, el.clientHeight];
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
        if (this.uiState.statusFilter === status) {
            this.uiState.statusFilter = null;
        } else {
            this.uiState.statusFilter = status;
        }
    }

    sortResults() {
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
        const cellSize = width / this.runnerState.tests.length;
        const colors = getColors();

        ctx.clearRect(0, 0, width, height);

        for (let i = 0; i < this.results.length; i++) {
            const x = Math.floor(i * cellSize);
            ctx.fillStyle = colors[COLORS_BY_ID[this.results[i]]];
            ctx.fillRect(x, 0, Math.ceil(cellSize), height);
        }
    }
}
