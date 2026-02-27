/** @odoo-module */

import { Component, computed, props, signal, types as t, useEffect, xml } from "@odoo/owl";
import { Test } from "../core/test";
import { refresh } from "../core/url";
import { elSignal, formatTime, throttle } from "../hoot_utils";
import { HootConfigMenu } from "./hoot_config_menu";
import { HootTestPath } from "./hoot_test_path";
import { HootTestResult } from "./hoot_test_result";
import { getConfigPlugin, getRunnerPlugin } from "./runner_plugin";

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
 * @param {import("@odoo/owl").Signal<HTMLElement | null>} containerRef
 * @param {import("@odoo/owl").Signal<HTMLElement | null>} handleRef
 * @param {() => any} allowDrag
 */
function useMovable(containerRef, handleRef, allowDrag) {
    /**
     * @param {PointerEvent} ev
     */
    function drag(ev) {
        const currentContainer = containerRef();
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
        const currentContainer = containerRef();
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
        const currentContainer = containerRef();
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
        const currentHandle = handleRef();
        if (currentHandle) {
            removeEventListener.call(currentHandle, "pointerdown", dragStart);
        }
    }

    function onEffect() {
        const currentHandle = handleRef();
        if (currentHandle) {
            addEventListener.call(currentHandle, "pointerdown", dragStart);
        }
        return effectCleanup;
    }

    function resetPosition() {
        containerRef()?.removeAttribute("style");
        dragEnd();
    }

    const throttledDrag = throttle(drag);

    let isDragging = false;
    let maxX = 0;
    let maxY = 0;
    let offsetX = 0;
    let offsetY = 0;

    useEffect(onEffect);

    return {
        resetPosition,
    };
}

/**
 * @typedef {import("../core/expect").Assertion} Assertion
 *
 * @typedef {import("../core/expect").CaseResult} CaseResult
 */

export class HootDebugToolBar extends Component {
    static components = { HootConfigMenu, HootTestPath, HootTestResult };
    static template = xml`
        <div
            class="${HootDebugToolBar.name} absolute start-0 bottom-0 max-w-full max-h-full flex p-4 z-4"
            t-att-class="{ 'w-full': this.isOpen() }"
            t-ref="this.rootRef"
        >
            <div class="flex flex-col w-full overflow-hidden rounded shadow bg-gray-200 dark:bg-gray-800">
                <div class="flex items-center gap-2 px-2">
                    <i
                        class="fa fa-bug text-cyan p-2"
                        t-att-class="{ 'cursor-move': !this.isOpen() }"
                        t-ref="this.handleRef"
                    />
                    <div class="flex gap-px rounded my-1 overflow-hidden min-w-fit">
                        <button
                            class="bg-btn px-2 py-1"
                            title="Exit debug mode (Ctrl + Esc)"
                            t-on-click.stop="this.exitDebugMode"
                        >
                            <i class="fa fa-sign-out" />
                        </button>
                        <t t-if="this.done">
                            <button
                                class="bg-btn px-2 py-1 animate-slide-left"
                                title="Restart test (F5)"
                                t-on-click.stop="this.refresh"
                            >
                                <i class="fa fa-refresh" />
                            </button>
                        </t>
                    </div>
                    <button
                        class="flex flex-1 items-center gap-1 truncate"
                        t-on-click.stop="this.toggleOpen"
                        title="Click to toggle details"
                    >
                        status:
                        <strong
                            t-attf-class="text-{{ this.info().className }}"
                            t-out="this.info().status"
                        />
                        <span class="hidden sm:flex items-center gap-1">
                            <span class="text-gray">-</span>
                            assertions:
                            <span class="contents text-emerald">
                                <strong t-out="this.info().passed" />
                                passed
                            </span>
                            <t t-if="this.info().failed">
                                <span class="text-gray">/</span>
                                <span class="contents text-rose">
                                    <strong t-out="this.info().failed" />
                                    failed
                                </span>
                            </t>
                        </span>
                        <span class="text-gray">-</span>
                        time:
                        <span
                            class="text-primary"
                            t-out="this.formatTime(this.props.test.lastResults?.duration, 'ms')"
                        />
                    </button>
                    <button class="p-2" t-on-click="this.toggleConfig">
                        <i class="fa fa-cog" />
                    </button>
                </div>
                <t t-if="this.isOpen()">
                    <div class="flex flex-col w-full sm:flex-row overflow-auto">
                        <HootTestResult open="'always'" test="this.props.test" t-key="this.done">
                            <HootTestPath canCopy="true" full="true" test="this.props.test" />
                        </HootTestResult>
                        <t t-if="this.isConfigOpen()">
                            <div class="flex flex-col gap-1 p-3 overflow-y-auto">
                                <HootConfigMenu />
                            </div>
                        </t>
                    </div>
                </t>
            </div>
        </div>
    `;

    // Props & plugins
    props = props({
        test: t.instanceOf(Test),
    });

    config = getConfigPlugin();
    runner = getRunnerPlugin();

    // Reactive values
    isConfigOpen = signal(false);
    isOpen = signal(false);
    info = computed(() => {
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
    });
    rootRef = elSignal(null);
    handleRef = elSignal(null);

    // Other members
    formatTime = formatTime;
    movable = useMovable(this.rootRef, this.handleRef, this.allowDrag.bind(this));
    refresh = refresh;

    get done() {
        return Boolean(this.runner.finishedTests().size); // subscribe to test being added as done
    }

    allowDrag() {
        return !this.isOpen();
    }

    exitDebugMode() {
        this.config.debugTest.set(false);
        this.runner.stop();
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

    toggleConfig() {
        this.isConfigOpen.set(!this.isOpen() || !this.isConfigOpen());
        if (this.isConfigOpen() && !this.isOpen()) {
            this.isOpen.set(true);
            this.movable.resetPosition();
        }
    }

    toggleOpen() {
        this.isOpen.set(!this.isOpen());
        if (this.isOpen()) {
            this.movable.resetPosition();
        }
    }
}
