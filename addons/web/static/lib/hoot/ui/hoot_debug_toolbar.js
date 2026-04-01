/** @odoo-module */

import { Component, onWillRender, useEffect, useRef, useState, xml } from "@odoo/owl";
import { Test } from "../core/test";
import { refresh } from "../core/url";
import { formatTime, throttle } from "../hoot_utils";
import { HootConfigMenu } from "./hoot_config_menu";
import { HootTestPath } from "./hoot_test_path";
import { HootTestResult } from "./hoot_test_result";

const {
    HTMLElement,
    innerHeight,
    innerWidth,
    Math: { max: $max, min: $min },
    Object: { assign: $assign },
} = globalThis;
const addWindowListener = window.addEventListener.bind(window);
const removeWindowListener = window.removeEventListener.bind(window);
const { addEventListener, removeEventListener } = HTMLElement.prototype;

/**
 * @param {string} containerRefName
 * @param {string} handleRefName
 * @param {() => any} allowDrag
 */
function useMovable(containerRefName, handleRefName, allowDrag) {
    function computeEffectDependencies() {
        return [(currentContainer = containerRef.el), (currentHandle = handleRef.el)];
    }

    /**
     * @param {PointerEvent} ev
     */
    function drag(ev) {
        if (!currentContainer || !isDragging) {
            return;
        }

        ev.preventDefault();

        const x = $max($min(maxX, ev.clientX - offsetX), 0);
        const y = $max($min(maxY, ev.clientY - offsetY), 0);
        $assign(currentContainer.style, {
            left: `${x}px`,
            top: `${y}px`,
        });
    }

    /**
     * @param {PointerEvent} [ev]
     */
    function dragEnd(ev) {
        if (!currentContainer || !isDragging) {
            return;
        }
        isDragging = false;

        ev?.preventDefault();

        removeWindowListener("pointermove", throttledDrag);
        removeWindowListener("pointerup", dragEnd);
    }

    /**
     * @param {PointerEvent} ev
     */
    function dragStart(ev) {
        if (!currentContainer || !allowDrag()) {
            return;
        }

        if (isDragging) {
            dragEnd(ev);
        } else {
            ev.preventDefault();
        }

        isDragging = true;

        addWindowListener("pointermove", throttledDrag);
        addWindowListener("pointerup", dragEnd);
        addWindowListener("keydown", dragEnd);

        const { x, y, width, height } = currentContainer.getBoundingClientRect();

        $assign(currentContainer.style, {
            left: `${x}px`,
            top: `${y}px`,
            width: `${width}px`,
            height: `${height}px`,
        });

        offsetX = ev.clientX - x;
        offsetY = ev.clientY - y;
        maxX = innerWidth - width;
        maxY = innerHeight - height;
    }

    function effectCleanup() {
        if (currentHandle) {
            removeEventListener.call(currentHandle, "pointerdown", dragStart);
        }
    }

    function onEffect() {
        if (currentHandle) {
            addEventListener.call(currentHandle, "pointerdown", dragStart);
        }
        return effectCleanup;
    }

    function resetPosition() {
        currentContainer?.removeAttribute("style");
        dragEnd();
    }

    const throttledDrag = throttle(drag);

    const containerRef = useRef(containerRefName);
    const handleRef = useRef(handleRefName);
    /** @type {HTMLElement | null} */
    let currentContainer = null;
    /** @type {HTMLElement | null} */
    let currentHandle = null;
    let isDragging = false;
    let maxX = 0;
    let maxY = 0;
    let offsetX = 0;
    let offsetY = 0;

    useEffect(onEffect, computeEffectDependencies);

    return {
        resetPosition,
    };
}

/**
 * @typedef {import("../core/expect").Assertion} Assertion
 *
 * @typedef {{
 *  test: Test;
 * }} HootDebugToolBarProps
 *
 * @typedef {import("../core/expect").CaseResult} CaseResult
 */

/** @extends {Component<HootDebugToolBarProps, import("../hoot").Environment>} */
export class HootDebugToolBar extends Component {
    static components = { HootConfigMenu, HootTestPath, HootTestResult };

    static props = {
        test: Test,
    };

    static template = xml`
        <div
            class="${HootDebugToolBar.name} absolute start-0 bottom-0 max-w-full max-h-full flex p-4 z-4"
            t-att-class="{ 'w-full': state.open }"
            t-ref="root"
        >
            <div class="flex flex-col w-full overflow-hidden rounded shadow bg-gray-200 dark:bg-gray-800">
                <div class="flex items-center gap-2 px-2">
                    <i
                        class="fa fa-bug text-cyan p-2"
                        t-att-class="{ 'cursor-move': !state.open }"
                        t-ref="handle"
                    />
                    <div class="flex gap-px rounded my-1 overflow-hidden min-w-fit">
                        <button
                            class="bg-btn px-2 py-1"
                            title="Exit debug mode (Ctrl + Esc)"
                            t-on-click.stop="exitDebugMode"
                        >
                            <i class="fa fa-sign-out" />
                        </button>
                        <t t-if="done">
                            <button
                                class="bg-btn px-2 py-1 animate-slide-left"
                                title="Restart test (F5)"
                                t-on-click.stop="refresh"
                            >
                                <i class="fa fa-refresh" />
                            </button>
                        </t>
                    </div>
                    <button
                        class="flex flex-1 items-center gap-1 truncate"
                        t-on-click.stop="toggleOpen"
                        title="Click to toggle details"
                    >
                        status:
                        <strong
                            t-attf-class="text-{{ info.className }}"
                            t-esc="info.status"
                        />
                        <span class="hidden sm:flex items-center gap-1">
                            <span class="text-gray">-</span>
                            assertions:
                            <span class="contents text-emerald">
                                <strong t-esc="info.passed" />
                                passed
                            </span>
                            <t t-if="info.failed">
                                <span class="text-gray">/</span>
                                <span class="contents text-rose">
                                    <strong t-esc="info.failed" />
                                    failed
                                </span>
                            </t>
                        </span>
                        <span class="text-gray">-</span>
                        time:
                        <span
                            class="text-primary"
                            t-esc="formatTime(props.test.lastResults?.duration, 'ms')"
                        />
                    </button>
                    <button class="p-2" t-on-click="toggleConfig">
                        <i class="fa fa-cog" />
                    </button>
                </div>
                <t t-if="state.open">
                    <div class="flex flex-col w-full sm:flex-row overflow-auto">
                        <HootTestResult open="'always'" test="props.test" t-key="done">
                            <HootTestPath canCopy="true" full="true" test="props.test" />
                        </HootTestResult>
                        <t t-if="state.configOpen">
                            <div class="flex flex-col gap-1 p-3 overflow-y-auto">
                                <HootConfigMenu />
                            </div>
                        </t>
                    </div>
                </t>
            </div>
        </div>
    `;

    formatTime = formatTime;
    refresh = refresh;

    get done() {
        return Boolean(this.runnerState.done.size); // subscribe to test being added as done
    }

    setup() {
        this.runnerState = useState(this.env.runner.state);
        this.state = useState({
            configOpen: false,
            open: false,
        });

        onWillRender(this.onWillRender.bind(this));

        this.movable = useMovable("root", "handle", this.allowDrag.bind(this));
    }

    allowDrag() {
        return !this.state.open;
    }

    exitDebugMode() {
        const { runner } = this.env;
        runner.config.debugTest = false;
        runner.stop();
    }

    getInfo() {
        const [status, className] = this.getStatus();
        const [assertPassed, assertFailed] = this.groupAssertions(
            this.props.test.lastResults?.getEvents("assertion")
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
                    return ["passed", "emerald"];
                case Test.FAILED:
                    return ["failed", "rose"];
                case Test.ABORTED:
                    return ["aborted", "amber"];
            }
        }
        return ["running", "cyan"];
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

    onWillRender() {
        this.info = this.getInfo();
    }

    toggleConfig() {
        this.state.configOpen = !this.state.open || !this.state.configOpen;
        if (this.state.configOpen && !this.state.open) {
            this.state.open = true;
            this.movable.resetPosition();
        }
    }

    toggleOpen() {
        this.state.open = !this.state.open;
        if (this.state.open) {
            this.movable.resetPosition();
        }
    }
}
