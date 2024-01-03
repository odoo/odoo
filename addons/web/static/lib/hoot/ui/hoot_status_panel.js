/** @odoo-module */

import { Component, onWillRender, useEffect, useRef, useState, xml } from "@odoo/owl";
import { batch, formatTime } from "../hoot_utils";
import { getTitle, setTitle } from "../mock/window";
import { getColors } from "./hoot_colors";
import { HootTestPath } from "./hoot_test_path";

/**
 * @typedef {{
 *  filter: "failed" | "passed" | "skipped" | "todo" | null;
 *  filterResults: (filter: string) => void;
 *  grouped: boolean;
 *  groupResults: () => void;
 *  sorted: "asc" | "desc" | false;
 *  sortResults: () => void;
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

    static props = {
        filter: [
            { value: "failed" },
            { value: "passed" },
            { value: "skipped" },
            { value: "todo" },
            { value: null },
        ],
        filterResults: Function,
        grouped: Boolean,
        groupResults: Function,
        sorted: [{ value: "asc" }, { value: "desc" }, { value: false }],
        sortResults: Function,
    };

    static template = xml`
        <div class="flex items-center justify-between gap-3 px-3 py-1 bg-gray-300 dark:bg-gray-700" t-att-class="state.className">
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
                        <strong class="text-primary" t-esc="state.done" />
                        tests completed
                        (<strong class="text-primary" t-esc="state.assertions" /> assertions,
                        total time: <strong class="text-primary" t-esc="env.runner.totalTime" />)
                    </span>
                    <span class="md:hidden flex items-center gap-1">
                        <i class="fa fa-clock-o" />
                        <strong class="text-primary" t-esc="env.runner.totalTime" />
                    </span>
                </t>
                <t t-if="state.runningTest">
                    <HootTestPath canCopy="false" test="state.runningTest" />
                </t>
                <t t-if="state.timer">
                    <span class="text-skip" t-esc="formatTime(state.timer, 's')" />
                </t>
            </div>
            <div class="flex gap-1">
                <t t-if="state.passed">
                    <t t-set="color" t-value="!props.filter or props.filter === 'passed' ? 'pass' : 'muted'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click="() => props.filterResults('passed')"
                        t-attf-title="Show {{ state.passed }} passed tests"
                    >
                        <i class="fa fa-check-circle" />
                        <t t-esc="state.passed" />
                    </button>
                </t>
                <t t-if="state.failed">
                    <t t-set="color" t-value="!props.filter or props.filter === 'failed' ? 'fail' : 'muted'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click="() => props.filterResults('failed')"
                        t-attf-title="Show {{ state.failed }} failed tests"
                    >
                        <i class="fa fa-times-circle" />
                        <t t-esc="state.failed" />
                    </button>
                </t>
                <t t-if="state.skipped">
                    <t t-set="color" t-value="!props.filter or props.filter === 'skipped' ? 'skip' : 'muted'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click="() => props.filterResults('skipped')"
                        t-attf-title="Show {{ state.skipped }} skipped tests"
                    >
                        <i class="fa fa-pause-circle" />
                        <t t-esc="state.skipped" />
                    </button>
                </t>
                <t t-if="state.todo">
                    <t t-set="color" t-value="!props.filter or props.filter === 'todo' ? 'todo' : 'muted'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click="() => props.filterResults('todo')"
                        t-attf-title="Show {{ state.todo }} tests to do"
                    >
                        <i class="fa fa-exclamation-circle" />
                        <t t-esc="state.todo" />
                    </button>
                </t>
                <button
                    class="p-1 transition-colors"
                    t-att-class="{ 'text-primary': props.grouped }"
                    title="Group by suite"
                    t-on-click="props.groupResults"
                >
                    <i class="fa fa-bars transition" />
                </button>
                <button
                    class="p-1 transition-colors"
                    t-att-class="{ 'text-primary': props.sorted }"
                    title="Sort by duration"
                    t-on-click="props.sortResults"
                >
                    <i
                        class="fa fa-filter transition"
                        t-att-class="{ 'rotate-180': props.sorted === 'asc' }"
                    />
                </button>
            </div>
        </div>
        <canvas t-ref="progress-canvas" class="flex h-1 w-full" />
    `;

    formatTime = formatTime;

    setup() {
        let expectsResult = false;
        const [addResult, flushResults] = batch((config, lastResults) => {
            this.state.assertions += lastResults.assertions.length;
            this.state.done++;
            this.state.tests++;
            if (!lastResults.pass) {
                this.state.failed++;
                this.results.push(COLORS_BY_NAME.fail);
            } else if (config.todo) {
                this.state.todo++;
                this.results.push(COLORS_BY_NAME.todo);
            } else {
                this.state.passed++;
                this.results.push(COLORS_BY_NAME.pass);
            }
            expectsResult = false;
        });

        const startTimer = () => {
            if (runner.config.headless) {
                return;
            }

            stopTimer();

            currentTestStart = performance.now();
            intervalId = setInterval(() => {
                this.state.timer = Math.floor(performance.now() - currentTestStart);
            }, 1000);
        };

        const stopTimer = () => {
            if (runner.config.headless) {
                return;
            }

            if (intervalId) {
                clearInterval(intervalId);
                intervalId = 0;
            }

            this.state.timer = 0;
        };

        const { runner } = this.env;
        let currentTestStart;
        this.canvasRef = useRef("progress-canvas");
        this.state = useState({
            className: "",
            /** @type {import("../core/test").Test | null} */
            runningTest: null,
            timer: null,
            // reporting
            assertions: 0,
            done: 0,
            failed: 0,
            passed: 0,
            skipped: 0,
            todo: 0,
            tests: 0,
        });
        this.runnerState = useState(runner.state);
        /** @type {number[]} */
        this.results = [];

        let intervalId = 0;

        runner.beforeAll(() => {
            this.results = [];
            this.state.debug = runner.debug;
        });

        runner.afterAll(() => {
            stopTimer();
            flushResults();

            this.state.runningTest = null;

            updateTitle(this.state.failed > 0);

            if (runner.config.fun) {
                const container = this.canvasRef.el.offsetParent;
                for (let i = 0; i < this.state.failed; i++) {
                    spawnIncentive(container, "😭");
                }
                for (let i = 0; i < this.state.passed; i++) {
                    spawnIncentive(container, "🦉");
                }
            }
        });

        runner.beforeEach((test) => {
            this.state.runningTest = test;

            startTimer();
        });

        runner.afterTestDone((test) => {
            if (!runner.debug) {
                stopTimer();
            }

            expectsResult = true;
            addResult(test.config, test.lastResults);
        });

        runner.onTestSkipped(() => {
            this.state.runningTest = null;
            this.state.skipped++;
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

    updateProgressBar() {
        const canvas = this.canvasRef.el;
        if (!canvas) {
            return;
        }

        const ctx = canvas.getContext("2d");
        const { width, height } = canvas;
        const cellSize = width / this.env.runner.includedTests.size;
        const colors = getColors();

        ctx.clearRect(0, 0, width, height);

        for (let i = 0; i < this.results.length; i++) {
            const x = Math.floor(i * cellSize);
            ctx.fillStyle = colors[COLORS_BY_ID[this.results[i]]];
            ctx.fillRect(x, 0, Math.ceil(cellSize), height);
        }
    }
}
