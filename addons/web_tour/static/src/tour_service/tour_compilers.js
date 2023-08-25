/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { debounce } from "@web/core/utils/timing";
import { isVisible } from "@web/core/utils/ui";
import { tourState } from "./tour_state";
import {
    callWithUnloadCheck,
    getConsumeEventType,
    getFirstVisibleElement,
    getJQueryElementFromSelector,
    getScrollParent,
    RunningTourActionHelper,
} from "./tour_utils";

/**
 * @typedef {import("@web/core/macro").MacroDescriptor} MacroDescriptor
 *
 * @typedef {import("../tour_service/tour_pointer_state").TourPointerState} TourPointerState
 *
 * @typedef {import("./tour_service").TourStep} TourStep
 *
 * @typedef {(stepIndex: number, step: TourStep, options: TourCompilerOptions) => MacroDescriptor[]} TourStepCompiler
 *
 * @typedef TourCompilerOptions
 * @property {Tour} tour
 * @property {number} stepDelay
 * @property {keepWatchBrowser} boolean
 * @property {showPointerDuration} number
 * @property {*} pointer - used for controlling the pointer of the tour
 */

/**
 * @param {string} selector - any valid jquery selector
 * @param {boolean} inModal
 * @param {string|undefined} shadowDOM - selector of the shadow root host
 * @returns {Element | undefined}
 */
function findTrigger(selector, inModal, shadowDOM) {
    const $target = $(shadowDOM ? document.querySelector(shadowDOM)?.shadowRoot : document);
    const $visibleModal = $target.find(".modal:visible").last();
    let $el;
    if (inModal !== false && $visibleModal.length) {
        $el = $visibleModal.find(selector);
    } else {
        $el = getJQueryElementFromSelector(selector, $target);
    }
    return getFirstVisibleElement($el).get(0);
}

/**
 * @param {string|undefined} shadowDOM - selector of the shadow root host
 */
function findExtraTrigger(selector, shadowDOM) {
    const $target = $(shadowDOM ? document.querySelector(shadowDOM)?.shadowRoot : document);
    const $el = getJQueryElementFromSelector(selector, $target);
    return getFirstVisibleElement($el).get(0);
}

function findStepTriggers(step) {
    const triggerEl = findTrigger(step.trigger, step.in_modal, step.shadow_dom);
    const altEl = findTrigger(step.alt_trigger, step.in_modal, step.shadow_dom);
    const skipEl = findTrigger(step.skip_trigger, step.in_modal, step.shadow_dom);

    // `extraTriggerOkay` should be true when `step.extra_trigger` is undefined.
    // No need for it to be in the modal.
    const extraTriggerOkay = step.extra_trigger
        ? findExtraTrigger(step.extra_trigger, step.shadow_dom)
        : true;

    return { triggerEl, altEl, extraTriggerOkay, skipEl };
}

/**
 * @param {TourStep} step
 */
function describeStep(step) {
    return step.content ? `${step.content} (trigger: ${step.trigger})` : step.trigger;
}

/**
 * @param {TourStep} step
 */
function describeFailedStepSimple(step, tour) {
    return `Tour ${tour.name} failed at step ${describeStep(step)}`;
}

/**
 * @param {TourStep} step
 * @param {Tour} tour
 */
function describeFailedStepDetailed(step, tour) {
    const offset = 3;
    const stepIndex = tour.steps.findIndex((s) => s === step);
    const start = stepIndex - offset >= 0 ? stepIndex - offset : 0;
    const end =
        stepIndex + offset + 1 <= tour.steps.length ? stepIndex + offset + 1 : tour.steps.length;
    let result = "";
    for (let i = start; i < end; i++) {
        const highlight = i === stepIndex;
        const stepString = JSON.stringify(
            tour.steps[i],
            (_key, value) => {
                if (typeof value === "function") {
                    return "[function]";
                } else {
                    return value;
                }
            },
            2
        );
        result += `\n${highlight ? "----- FAILING STEP -----\n" : ""}${stepString},${
            highlight ? "\n-----------------------" : ""
        }`;
    }
    return `${describeFailedStepSimple(step, tour)}\n\n${result.trim()}`;
}

/**
 * Returns the element that will be used in listening to the `consumeEvent`.
 * @param {HTMLElement} el
 * @param {string} consumeEvent
 */
function getAnchorEl(el, consumeEvent) {
    if (consumeEvent === "drag") {
        // jQuery-ui draggable triggers 'drag' events on the .ui-draggable element,
        // but the tip is attached to the .ui-draggable-handle element which may
        // be one of its children (or the element itself)
        return el.closest(".ui-draggable, .o_draggable");
    }
    if (consumeEvent === "input" && !["textarea", "input"].includes(el.tagName.toLowerCase())) {
        return el.closest("[contenteditable='true']");
    }
    if (consumeEvent === "sort") {
        // when an element is dragged inside a sortable container (with classname
        // 'ui-sortable'), jQuery triggers the 'sort' event on the container
        return el.closest(".ui-sortable, .o_sortable");
    }
    return el;
}

/**
 * IMPROVEMENT: Consider transitioning (moving) elements?
 * @param {Element} el
 * @param {TourStep} step
 */
function canContinue(el, step) {
    const rootNode = el.getRootNode();
    const isInDoc =
        rootNode instanceof ShadowRoot
            ? el.ownerDocument.contains(rootNode.host)
            : el.ownerDocument.contains(el);
    const isElement = el instanceof el.ownerDocument.defaultView.Element || el instanceof Element;
    const isBlocked = document.body.classList.contains("o_ui_blocked") || document.querySelector(".o_blockUI");
    return (
        isInDoc &&
        isElement &&
        !isBlocked &&
        (!step.allowInvisible ? isVisible(el) : true) &&
        (!el.disabled || step.isCheck)
    );
}

/**
 * @param {Object} params
 * @param {HTMLElement} params.anchorEl
 * @param {string} params.consumeEvent
 * @param {() => void} params.onMouseEnter
 * @param {() => void} params.onMouseLeave
 * @param {(ev: Event) => any} params.onScroll
 * @param {(ev: Event) => any} params.onConsume
 */
function setupListeners({
    anchorEl,
    consumeEvent,
    onMouseEnter,
    onMouseLeave,
    onScroll,
    onConsume,
}) {
    anchorEl.addEventListener(consumeEvent, onConsume);
    anchorEl.addEventListener("mouseenter", onMouseEnter);
    anchorEl.addEventListener("mouseleave", onMouseLeave);

    const cleanups = [
        () => {
            anchorEl.removeEventListener(consumeEvent, onConsume);
            anchorEl.removeEventListener("mouseenter", onMouseEnter);
            anchorEl.removeEventListener("mouseleave", onMouseLeave);
        },
    ];

    const scrollEl = getScrollParent(anchorEl);
    if (scrollEl) {
        const debouncedOnScroll = debounce(onScroll, 50);
        scrollEl.addEventListener("scroll", debouncedOnScroll);
        cleanups.push(() => scrollEl.removeEventListener("scroll", debouncedOnScroll));
    }

    return () => {
        while (cleanups.length) {
            cleanups.pop()();
        }
    };
}

/** @type {TourStepCompiler} */
export function compileStepManual(stepIndex, step, options) {
    const { tour, pointer, onStepConsummed } = options;
    let proceedWith = null;
    let removeListeners = () => {};

    return [
        {
            action: () => console.log(step.trigger),
        },
        {
            trigger: () => {
                removeListeners();

                if (proceedWith) {
                    return proceedWith;
                }

                const { triggerEl, altEl, extraTriggerOkay, skipEl } = findStepTriggers(step);

                if (skipEl) {
                    return skipEl;
                }

                const stepEl = extraTriggerOkay && (triggerEl || altEl);

                if (stepEl && canContinue(stepEl, step)) {
                    const consumeEvent = step.consumeEvent || getConsumeEventType(stepEl, step.run);
                    const anchorEl = getAnchorEl(stepEl, consumeEvent);
                    const debouncedToggleOpen = debounce(pointer.showContent, 50, true);

                    const updatePointer = () => {
                        pointer.setState({
                            onMouseEnter: () => debouncedToggleOpen(true),
                            onMouseLeave: () => debouncedToggleOpen(false),
                        });
                        pointer.pointTo(anchorEl, step);
                    };

                    removeListeners = setupListeners({
                        anchorEl,
                        consumeEvent,
                        onMouseEnter: () => pointer.showContent(true),
                        onMouseLeave: () => pointer.showContent(false),
                        onScroll: updatePointer,
                        onConsume: () => {
                            proceedWith = stepEl;
                            pointer.hide();
                        },
                    });

                    updatePointer();
                } else {
                    pointer.hide();
                }
            },
            action: () => {
                tourState.set(tour.name, "currentIndex", stepIndex + 1);
                pointer.hide();
                proceedWith = null;
                onStepConsummed(tour, step);
            },
        },
    ];
}

let tourTimeout;

/** @type {TourStepCompiler} */
export function compileStepAuto(stepIndex, step, options) {
    const { tour, pointer, stepDelay, keepWatchBrowser, showPointerDuration, onStepConsummed } = options;
    let skipAction = false;
    return [
        {
            action: async () => {
                // This delay is important for making the current set of tour tests pass.
                // IMPROVEMENT: Find a way to remove this delay.
                await new Promise(resolve => requestAnimationFrame(resolve))
            },
        },
        {
            action: async () => {
                skipAction = false;
                console.log(`Tour ${tour.name} on step: '${describeStep(step)}'`);
                if (!keepWatchBrowser) {
                    clearTimeout(tourTimeout);
                    tourTimeout = setTimeout(() => {
                        // The logged text shows the relative position of the failed step.
                        // Useful for finding the failed step.
                        console.warn(describeFailedStepDetailed(step, tour));
                        // console.error notifies the test runner that the tour failed.
                        console.error(describeFailedStepSimple(step, tour));
                    }, (step.timeout || 10000) + stepDelay);
                }
                await new Promise((resolve) => browser.setTimeout(resolve, stepDelay));
            },
        },
        {
            trigger: () => {
                const { triggerEl, altEl, extraTriggerOkay, skipEl } = findStepTriggers(step);

                let stepEl = extraTriggerOkay && (triggerEl || altEl);

                if (skipEl) {
                    skipAction = true;
                    stepEl = skipEl;
                }

                if (!stepEl) {
                    return false;
                }

                return canContinue(stepEl, step) && stepEl;
            },
            action: async (stepEl) => {
                tourState.set(tour.name, "currentIndex", stepIndex + 1);

                if (skipAction) {
                    return;
                }

                const consumeEvent = step.consumeEvent || getConsumeEventType(stepEl, step.run);
                // When in auto mode, we are not waiting for an event to be consumed, so the
                // anchor is just the step element.
                const $anchorEl = $(stepEl);

                if (showPointerDuration > 0) {
                    // Useful in watch mode.
                    pointer.pointTo($anchorEl.get(0), step);
                    await new Promise((r) => browser.setTimeout(r, showPointerDuration));
                    pointer.hide();
                }

                // TODO: Delegate the following routine to the `ACTION_HELPERS` in the macro module.
                const actionHelper = new RunningTourActionHelper({
                    consume_event: consumeEvent,
                    $anchor: $anchorEl,
                });

                let result;
                if (typeof step.run === "function") {
                    const willUnload = await callWithUnloadCheck(() =>
                        // `this.$anchor` is expected in many `step.run`.
                        step.run.call({ $anchor: $anchorEl }, actionHelper)
                    );
                    result = willUnload && "will unload";
                } else if (step.run !== undefined) {
                    const m = step.run.match(/^([a-zA-Z0-9_]+) *(?:\(? *(.+?) *\)?)?$/);
                    actionHelper[m[1]](m[2]);
                } else if (!step.isCheck) {
                    if (stepIndex === tour.steps.length - 1) {
                        console.warn('Tour %s: ignoring action (auto) of last step', tour.name);
                    } else {
                        actionHelper.auto();
                    }
                }

                return result;
            },
        },
        {
            action: () => {
                onStepConsummed(tour, step);
            },
        },
    ];
}

/**
 * @param {import("./tour_service").Tour} tour
 * @param {object} options
 * @param {TourStep[]} options.filteredSteps
 * @param {TourStepCompiler} options.stepCompiler
 * @param {*} options.pointer
 * @param {number} options.stepDelay
 * @param {boolean} options.keepWatchBrowser
 * @param {number} options.showPointerDuration
 * @param {number} options.checkDelay
 * @param {(import("./tour_service").Tour) => void} options.onTourEnd
 */
export function compileTourToMacro(tour, options) {
    const {
        filteredSteps,
        stepCompiler,
        pointer,
        stepDelay,
        keepWatchBrowser,
        showPointerDuration,
        checkDelay,
        onStepConsummed,
        onTourEnd,
    } = options;
    const currentStepIndex = tourState.get(tour.name, "currentIndex");
    return {
        ...tour,
        checkDelay,
        steps: filteredSteps
            .reduce((newSteps, step, i) => {
                if (i < currentStepIndex) {
                    // Don't include steps before the current index because they're already done.
                    return newSteps;
                } else {
                    return [
                        ...newSteps,
                        ...stepCompiler(i, step, {
                            tour,
                            pointer,
                            stepDelay,
                            keepWatchBrowser,
                            showPointerDuration,
                            onStepConsummed,
                        }),
                    ];
                }
            }, [])
            .concat([
                {
                    action() {
                        tourState.clear(tour.name);
                        onTourEnd(tour);
                        clearTimeout(tourTimeout);
                    },
                },
            ]),
    };
}
