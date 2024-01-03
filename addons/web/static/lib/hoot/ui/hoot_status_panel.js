/** @odoo-module */

import { Component, onWillRender, useEffect, useRef, useState, xml } from "@odoo/owl";
import { getStyle } from "@web/../lib/hoot-dom/helpers/dom";
import { getTitle, setTitle } from "../mock/window";
import { batch } from "../hoot_utils";
import { HootTestPath } from "./hoot_test_path";
import { Test } from "../core/test";

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
 * @param {string} content
 */
const spawnParticle = (content) => {
    const element = document.createElement("div");
    const params = [
        `--_content: '${content}'`,
        `--_fly-duration: ${randInt(2_000, 3_000)}`,
        `--_size: ${randInt(32, 48)}`,
        `--_wiggle-duration: ${randInt(800, 2_000)}`,
        `--_wiggle-range: ${randInt(5, 30)}`,
        `--_x: ${randInt(0, 100)}`,
        `--_y: ${randInt(100, 150)}`,
    ];
    element.setAttribute("class", `hoot-particle position-fixed`);
    element.setAttribute("style", params.join(";"));

    document.body.appendChild(element);

    /** @param {AnimationEvent} ev */
    const onEnd = (ev) => ev.animationName === "hoot-particle-slide-up" && element.remove();
    element.addEventListener("animationend", onEnd);
    element.addEventListener("animationcancel", onEnd);

    return element;
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
    0: "--hoot-pass",
    1: "--hoot-fail",
    2: "--hoot-skip",
    3: "--hoot-todo",
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

/** @extends Component<HootStatusPanelProps, import("../hoot").Environment> */
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
        <div class="hoot-status d-flex align-items-center justify-content-between gap-3 px-3 py-1" t-att-class="state.className">
            <div class="d-flex align-items-center gap-2 overflow-hidden">
                <t t-if="state.status === 'ready'">
                    Ready
                </t>
                <t t-elif="state.status === 'running'">
                    <i t-if="state.debug" class="hoot-text-skip fa fa-bug" title="Debugging" />
                    <div
                        t-else=""
                        class="hoot-text-primary spinner-border spinner-border-sm"
                        style="min-width: 1rem;"
                        role="status"
                        title="Running"
                    >
                        <span class="visually-hidden">Running</span>
                    </div>
                </t>
                <t t-else="">
                    <span class="d-none d-md-block">
                        <strong class="hoot-text-primary" t-esc="state.assertions" />
                        assertions over
                        <strong class="hoot-text-primary" t-esc="state.done" />
                        tests completed
                        (total time: <strong class="hoot-text-primary" t-esc="env.runner.totalTime" />)
                    </span>
                    <span class="d-md-none d-flex align-items-center gap-1">
                        <i class="fa fa-clock-o" />
                        <strong class="hoot-text-primary" t-esc="env.runner.totalTime" />
                    </span>
                </t>
                <t t-if="state.runningTest">
                    <HootTestPath canCopy="false" test="state.runningTest" />
                </t>
                <t t-if="state.timer !== null">
                    <span class="hoot-text-skip" t-attf-title="Running for {{ state.timer }} seconds">
                        (<t t-esc="state.timer" />s)
                    </span>
                </t>
            </div>
            <div class="d-flex gap-1">
                <t t-if="state.passed">
                    <t t-set="color" t-value="!props.filter or props.filter === 'passed' ? 'pass' : 'muted'" />
                    <button
                        t-attf-class="hoot-text-{{ color }} hoot-transition-colors d-flex align-items-center gap-1 p-1 fw-bold"
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
                        t-attf-class="hoot-text-{{ color }} hoot-transition-colors d-flex align-items-center gap-1 p-1 fw-bold"
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
                        t-attf-class="hoot-text-{{ color }} hoot-transition-colors d-flex align-items-center gap-1 p-1 fw-bold"
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
                        t-attf-class="hoot-text-{{ color }} hoot-transition-colors d-flex align-items-center gap-1 p-1 fw-bold"
                        t-on-click="() => props.filterResults('todo')"
                        t-attf-title="Show {{ state.todo }} tests to do"
                    >
                        <i class="fa fa-exclamation-circle" />
                        <t t-esc="state.todo" />
                    </button>
                </t>
                <button
                    class="p-1"
                    t-att-class="{ 'hoot-text-primary': props.grouped }"
                    title="Group by suite"
                    t-on-click="props.groupResults"
                >
                    <i class="fa fa-bars" />
                </button>
                <button
                    class="p-1"
                    t-att-class="{ 'hoot-text-primary': props.sorted }"
                    title="Sort by duration"
                    t-on-click="props.sortResults"
                >
                    <i class="fa fa-filter" />
                </button>
            </div>
        </div>
        <canvas t-ref="progress-canvas" class="d-flex w-100" style="height: 0.25rem;" />
    `;

    setup() {
        const addResult = batch((config, lastResults) => {
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
        });

        const startTimer = () => {
            if (runner.config.headless) {
                return;
            }
            stopTimer();
            currentTestStart = performance.now();
            intervalId = setInterval(() => {
                this.state.timer = Math.floor((performance.now() - currentTestStart) / 1000);
                intervalId = 0;
            }, 1000);
        };

        const stopTimer = () => {
            if (runner.config.headless) {
                return;
            }
            if (intervalId) {
                clearInterval(intervalId);
            }
            this.state.timer = null;
        };

        const { runner } = this.env;
        let currentTestStart;
        this.canvasRef = useRef("progress-canvas");
        this.state = useState({
            className: "",
            /** @type {import("../core/test").Test | null} */
            runningTest: null,
            status: "ready",
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
        /** @type {number[]} */
        this.results = [];
        /** @type {Record<number, string>} */
        this.colors = {};

        let intervalId = 0;

        runner.beforeAll(() => {
            this.results = [];
            this.state.debug = runner.debug;
            this.state.status = runner.status;
        });

        runner.afterAll(() => {
            stopTimer();

            this.state.runningTest = null;
            this.state.status = runner.status;

            updateTitle(this.state.failed > 0);

            if (runner.config.fun) {
                for (let i = 0; i < this.state.failed; i++) {
                    spawnParticle("😭");
                }
                for (let i = 0; i < this.state.passed; i++) {
                    spawnParticle("🦉");
                }
            }
        });

        runner.beforeEach((test) => {
            this.state.runningTest = test;
            this.state.timer = 0;

            startTimer();
        });

        runner.afterTestDone((test) => {
            if (!runner.debug) {
                stopTimer();
            }

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

                    const style = getStyle(el);
                    this.colors = Object.fromEntries(
                        Object.entries(COLORS_BY_ID).map(([id, name]) => [
                            id,
                            style.getPropertyValue(name),
                        ])
                    );
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

        ctx.clearRect(0, 0, width, height);

        for (let i = 0; i < this.results.length; i++) {
            const x = Math.floor(i * cellSize);
            ctx.fillStyle = this.colors[this.results[i]];
            ctx.fillRect(x, 0, Math.ceil(cellSize), height);
        }
    }
}
