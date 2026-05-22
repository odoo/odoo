/** @odoo-module */

import { Component, plugin, signal, types as t, useEffect, xml } from "@odoo/owl";
import { getColorHex } from "../../hoot-dom/hoot_dom_utils";
import { Test } from "../core/test";
import { formatTime } from "../hoot_utils";
import { getTitle, setTitle } from "../mock/window";
import { onColorSchemeChange } from "./hoot_colors";
import { HootTestPath } from "./hoot_test_path";
import { getConfigPlugin, getRunnerPlugin } from "./runner_plugin";
import { UiPlugin } from "./ui_plugin";

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

export class HootStatusPanel extends Component {
    static components = { HootTestPath };
    static template = xml`
        <div
            class="${HootStatusPanel.name} flex items-center justify-between gap-3 px-3 py-1 min-h-10 bg-gray-300 dark:bg-gray-700"
        >
            <div class="flex items-center gap-2 overflow-hidden">
                <t t-if="this.runner.status() === 'ready'">
                    Ready
                </t>
                <t t-elif="this.runner.status() === 'running'">
                    <i t-if="this.isDebugging()" class="text-cyan fa fa-bug" title="Debugging" />
                    <div
                        t-else=""
                        class="animate-spin shrink-0 grow-0 w-4 h-4 border-2 border-emerald border-t-transparent rounded-full"
                        role="status"
                        title="Running"
                    />
                    <strong class="text-primary" t-out="this.runner.totalTime" />
                </t>
                <t t-else="">
                    <span class="hidden md:block">
                        <strong class="text-primary" t-out="this.runner.reporting.tests" />
                        tests completed
                        (total time: <strong class="text-primary" t-out="this.runner.totalTime" />
                        <t t-if="this.runner.aborted">, run aborted by user</t>)
                    </span>
                    <span class="md:hidden flex items-center gap-1">
                        <i class="fa fa-clock-o" />
                        <strong class="text-primary" t-out="this.runner.totalTime" />
                    </span>
                </t>
                <t t-if="this.runner.currentTest()">
                    <HootTestPath test="this.runner.currentTest()" />
                </t>
                <t t-if="this.timer()">
                    <span class="text-cyan" t-out="this.formatTime(this.timer(), 's')" />
                </t>
            </div>
            <div class="flex items-center gap-1">
                <t t-if="this.runner.reporting.passed">
                    <t t-set="color" t-value="!this.ui.statusFilter() or this.ui.statusFilter() === 'passed' ? 'emerald' : 'gray'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click.stop="() => this.ui.statusFilter.set('passed')"
                        t-attf-title="Show {{ this.runner.reporting.passed }} passed tests"
                    >
                        <i class="fa fa-check-circle" />
                        <t t-out="this.runner.reporting.passed" />
                    </button>
                </t>
                <t t-if="this.runner.reporting.failed">
                    <t t-set="color" t-value="!this.ui.statusFilter() or this.ui.statusFilter() === 'failed' ? 'rose' : 'gray'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click.stop="() => this.ui.statusFilter.set('failed')"
                        t-attf-title="Show {{ this.runner.reporting.failed }} failed tests"
                    >
                        <i class="fa fa-times-circle" />
                        <t t-out="this.runner.reporting.failed" />
                    </button>
                </t>
                <t t-if="this.runner.reporting.skipped">
                    <t t-set="color" t-value="!this.ui.statusFilter() or this.ui.statusFilter() === 'skipped' ? 'cyan' : 'gray'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click.stop="() => this.ui.statusFilter.set('skipped')"
                        t-attf-title="Show {{ this.runner.reporting.skipped }} skipped tests"
                    >
                        <i class="fa fa-pause-circle" />
                        <t t-out="this.runner.reporting.skipped" />
                    </button>
                </t>
                <t t-if="this.runner.reporting.todo">
                    <t t-set="color" t-value="!this.ui.statusFilter() or this.ui.statusFilter() === 'todo' ? 'purple' : 'gray'" />
                    <button
                        t-attf-class="text-{{ color }} transition-colors flex items-center gap-1 p-1 font-bold"
                        t-on-click.stop="() => this.ui.statusFilter.set('todo')"
                        t-attf-title="Show {{ this.runner.reporting.todo }} tests to do"
                    >
                        <i class="fa fa-exclamation-circle" />
                        <t t-out="this.runner.reporting.todo" />
                    </button>
                </t>
                <t t-if="this.ui.totalResults() gt this.ui.resultsPerPage()">
                    <t t-set="lastPage" t-value="this.getLastPage()" />
                    <div class="flex gap-1 animate-slide-left">
                        <button
                            class="px-1 transition-color"
                            title="Previous page"
                            t-att-disabled="this.ui.resultsPage() === 0"
                            t-on-click.stop="this.previousPage"
                        >
                            <i class="fa fa-chevron-left" />
                        </button>
                        <strong class="text-primary" t-out="this.ui.resultsPage() + 1" />
                        <span class="text-gray">/</span>
                        <t t-out="lastPage + 1" />
                        <button
                            class="px-1 transition-color"
                            title="Next page"
                            t-att-disabled="this.ui.resultsPage() === lastPage"
                            t-on-click.stop="this.nextPage"
                        >
                            <i class="fa fa-chevron-right" />
                        </button>
                    </div>
                </t>
            </div>
        </div>
        <canvas t-ref="this.canvasRef" class="flex h-1 w-full" />
    `;

    // Props & plugins
    config = getConfigPlugin();
    runner = getRunnerPlugin();
    ui = plugin(UiPlugin);

    // Reactive values
    canvasRef = signal(null, { type: t.ref(HTMLCanvasElement) });
    timer = signal(0, { type: t.number() });
    progressBarIndex = signal(0, { type: t.number() });
    isDebugging = signal(false, { type: t.boolean() });

    // Other members
    currentTestStart = 0;
    formatTime = formatTime;
    intervalId = 0;

    setup() {
        this.runner.beforeAll(this.globalSetup.bind(this));
        this.runner.afterAll(this.globalCleanup.bind(this));
        if (!this.runner.headless) {
            this.runner.beforeEach(this.startTimer.bind(this));
            this.runner.afterPostTest(this.stopTimer.bind(this));
        }

        useEffect(() => {
            const canvas = this.canvasRef();
            if (!canvas) {
                return;
            }
            [canvas.width, canvas.height] = [canvas.clientWidth, canvas.clientHeight];
            canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
        });

        onColorSchemeChange(this.onColorSchemeChange.bind(this));

        useEffect(this.updateProgressBar.bind(this));
    }

    getLastPage() {
        const { resultsPerPage, totalResults } = this.ui;
        return $max($floor((totalResults() - 1) / resultsPerPage()), 0);
    }

    globalCleanup() {
        if (!this.runner.headless) {
            this.stopTimer();
        }
        updateTitle(this.runner.reporting.failed > 0);

        if (this.config.fun()) {
            for (let i = 0; i < this.runner.reporting.failed; i++) {
                spawnIncentive("😭");
            }
            for (let i = 0; i < this.runner.reporting.passed; i++) {
                spawnIncentive("🦉");
            }
        }
    }

    globalSetup() {
        this.isDebugging.set(this.runner.debug);
    }

    nextPage() {
        this.ui.resultsPage.set($min(this.ui.resultsPage() + 1, this.getLastPage()));
    }

    onColorSchemeChange() {
        this.progressBarIndex.set(0);
    }

    previousPage() {
        this.ui.resultsPage.set($max(this.ui.resultsPage() - 1, 0));
    }

    startTimer() {
        this.stopTimer();

        this.currentTestStart = $now();
        this.intervalId = setInterval(() => {
            this.timer.set(
                $floor(($now() - this.currentTestStart) / TIMER_PRECISION) * TIMER_PRECISION
            );
        }, TIMER_PRECISION);
    }

    stopTimer() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = 0;
        }

        this.timer.set(0);
    }

    updateProgressBar() {
        const canvas = this.canvasRef();
        if (!canvas) {
            return;
        }

        const ctx = canvas.getContext("2d");
        const { width, height } = canvas;
        const doneList = [...this.runner.finishedTests()];
        const cellSize = width / this.runner.filteredTests().length;
        const minSize = $ceil(cellSize);

        while (this.progressBarIndex() < doneList.length) {
            const test = doneList[this.progressBarIndex()];
            const x = $floor(this.progressBarIndex() * cellSize);
            switch (test.status()) {
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
            this.progressBarIndex.set(this.progressBarIndex() + 1);
        }
    }
}
