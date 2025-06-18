/** @odoo-module */

import { Component, onWillRender, useEffect, useRef, useState, xml } from "@odoo/owl";
import { getColorHex } from "../../hoot-dom/hoot_dom_utils";
import { Test } from "../core/test";
import { formatTime } from "../hoot_utils";
import { getTitle, setTitle } from "../mock/window";
import { onColorSchemeChange } from "./hoot_colors";
import { HootTestPath } from "./hoot_test_path";

/**
 * @typedef {import("../core/runner").Runner} Runner
 *
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
 * @param {HTMLCanvasElement | null} canvas
 */
function setupCanvas(canvas) {
    if (!canvas) {
        return;
    }
    [canvas.width, canvas.height] = [canvas.clientWidth, canvas.clientHeight];
    canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
}

/**
 * @param {number} min
 * @param {number} max
 */
function randInt(min, max) {
    return $floor($random() * (max - min + 1)) + min;
}

/**
 * @param {string} content
 */
function spawnIncentive(content) {
    const incentive = document.createElement("div");
    const params = [
        `--_content: '${content}'`,
        `--_fly-duration: ${randInt(2000, 3000)}`,
        `--_size: ${randInt(32, 48)}`,
        `--_wiggle-duration: ${randInt(800, 2000)}`,
        `--_wiggle-range: ${randInt(5, 30)}`,
        `--_x: ${randInt(0, 100)}`,
        `--_y: ${randInt(100, 150)}`,
    ];
    incentive.setAttribute("class", `incentive fixed`);
    incentive.setAttribute("style", params.join(";"));

    /** @param {AnimationEvent} ev */
    function onEnd(ev) {
        return ev.animationName === "animation-incentive-travel" && incentive.remove();
    }
    incentive.addEventListener("animationend", onEnd);
    incentive.addEventListener("animationcancel", onEnd);

    document.querySelector("hoot-container").shadowRoot.appendChild(incentive);
}

/**
 * @param {boolean} failed
 */
function updateTitle(failed) {
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
}

const TIMER_PRECISION = 100; // in ms
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
                    <i t-if="state.debug" class="text-cyan fa fa-bug" title="Debugging" />
                    <div
                        t-else=""
                        class="animate-spin shrink-0 grow-0 w-4 h-4 border-2 border-emerald border-t-transparent rounded-full"
                        role="status"
                        title="Running"
                    />
                    <strong class="text-primary" t-esc="env.runner.totalTime" />
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
                    <span class="text-cyan" t-esc="formatTime(state.timer, 's')" />
                </t>
            </div>
            <div class="flex items-center gap-1">
                <t t-if="runnerReporting.passed">
                    <t t-set="color" t-value="!uiState.statusFilter or uiState.statusFilter === 'passed' ? 'emerald' : 'gray'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click.stop="() => this.filterResults('passed')"
                        t-attf-title="Show {{ runnerReporting.passed }} passed tests"
                    >
                        <i class="fa fa-check-circle" />
                        <t t-esc="runnerReporting.passed" />
                    </button>
                </t>
                <t t-if="runnerReporting.failed">
                    <t t-set="color" t-value="!uiState.statusFilter or uiState.statusFilter === 'failed' ? 'rose' : 'gray'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click.stop="() => this.filterResults('failed')"
                        t-attf-title="Show {{ runnerReporting.failed }} failed tests"
                    >
                        <i class="fa fa-times-circle" />
                        <t t-esc="runnerReporting.failed" />
                    </button>
                </t>
                <t t-if="runnerReporting.skipped">
                    <t t-set="color" t-value="!uiState.statusFilter or uiState.statusFilter === 'skipped' ? 'cyan' : 'gray'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click.stop="() => this.filterResults('skipped')"
                        t-attf-title="Show {{ runnerReporting.skipped }} skipped tests"
                    >
                        <i class="fa fa-pause-circle" />
                        <t t-esc="runnerReporting.skipped" />
                    </button>
                </t>
                <t t-if="runnerReporting.todo">
                    <t t-set="color" t-value="!uiState.statusFilter or uiState.statusFilter === 'todo' ? 'purple' : 'gray'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click.stop="() => this.filterResults('todo')"
                        t-attf-title="Show {{ runnerReporting.todo }} tests to do"
                    >
                        <i class="fa fa-exclamation-circle" />
                        <t t-esc="runnerReporting.todo" />
                    </button>
                </t>
                <t t-if="uiState.totalResults gt uiState.resultsPerPage">
                    <t t-set="lastPage" t-value="getLastPage()" />
                    <div class="flex gap-1 animate-slide-left">
                        <button
                            class="px-1 transition-color"
                            title="Previous page"
                            t-att-disabled="uiState.resultsPage === 0"
                            t-on-click.stop="previousPage"
                        >
                            <i class="fa fa-chevron-left" />
                        </button>
                        <strong class="text-primary" t-esc="uiState.resultsPage + 1" />
                        <span class="text-gray">/</span>
                        <t t-esc="lastPage + 1" />
                        <button
                            class="px-1 transition-color"
                            title="Next page"
                            t-att-disabled="uiState.resultsPage === lastPage"
                            t-on-click.stop="nextPage"
                        >
                            <i class="fa fa-chevron-right" />
                        </button>
                    </div>
                </t>
            </div>
        </div>
        <canvas t-ref="progress-canvas" class="flex h-1 w-full" />
    `;

    currentTestStart;
    formatTime = formatTime;
    intervalId = 0;

    setup() {
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

        runner.beforeAll(this.globalSetup.bind(this));
        runner.afterAll(this.globalCleanup.bind(this));
        if (!runner.config.headless) {
            runner.beforeEach(this.startTimer.bind(this));
            runner.afterPostTest(this.stopTimer.bind(this));
        }

        useEffect(setupCanvas, () => [this.canvasRef.el]);

        onColorSchemeChange(this.onColorSchemeChange.bind(this));
        onWillRender(this.updateProgressBar.bind(this));
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

    /**
     * @param {Runner} runner
     */
    globalCleanup(runner) {
        if (!runner.config.headless) {
            this.stopTimer();
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
    }

    /**
     * @param {Runner} runner
     */
    globalSetup(runner) {
        this.state.debug = runner.debug;
    }

    nextPage() {
        this.uiState.resultsPage = $min(this.uiState.resultsPage + 1, this.getLastPage());
    }

    onColorSchemeChange() {
        this.progressBarIndex = 0;
        this.updateProgressBar();
    }

    previousPage() {
        this.uiState.resultsPage = $max(this.uiState.resultsPage - 1, 0);
    }

    startTimer() {
        this.stopTimer();

        this.currentTestStart = $now();
        this.intervalId = setInterval(() => {
            this.state.timer =
                $floor(($now() - this.currentTestStart) / TIMER_PRECISION) * TIMER_PRECISION;
        }, TIMER_PRECISION);
    }

    stopTimer() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = 0;
        }

        this.state.timer = 0;
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
        const minSize = $ceil(cellSize);

        while (this.progressBarIndex < done.size) {
            const test = doneList[this.progressBarIndex];
            const x = $floor(this.progressBarIndex * cellSize);
            switch (test.status) {
                case Test.ABORTED:
                    ctx.fillStyle = getColorHex("amber");
                    break;
                case Test.FAILED:
                    ctx.fillStyle = getColorHex("rose");
                    break;
                case Test.PASSED:
                    ctx.fillStyle = test.config.todo
                        ? getColorHex("purple")
                        : getColorHex("emerald");
                    break;
                case Test.SKIPPED:
                    ctx.fillStyle = getColorHex("cyan");
                    break;
            }
            ctx.fillRect(x, 0, minSize, height);
            this.progressBarIndex++;
        }
    }
}
