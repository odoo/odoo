/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { debounce } from "@web/core/utils/timing";
import { _legacyIsVisible, isVisible } from "@web/core/utils/ui";
import { omit, pick } from "@web/core/utils/objects";
import { tourState } from "./tour_state";
import * as hoot from "@odoo/hoot-dom";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import {
    callWithUnloadCheck,
    getConsumeEventType,
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
 * @param {string} selector - any valid Hoot selector
 * @param {string|undefined} shadowDOM - selector of the shadow root host
 * @param {boolean} inModal
 * @returns {Array<Element>}
 */
function findTrigger(selector, shadowDOM, inModal) {
    const target = shadowDOM ? document.querySelector(shadowDOM)?.shadowRoot : document;
    let nodes;
    if (inModal !== false) {
        const visibleModal = hoot.queryAll(".modal", { root: target, visible: true }).at(-1);
        if (visibleModal) {
            nodes = hoot.queryAll(selector, { root: visibleModal });
        }
    }
    if (!nodes) {
        nodes = hoot.queryAll(selector, { root: target });        
    }
    return nodes;
}

/**
 * @param {Tour} tour
 * @param {TourStep} step
 * @param {"trigger"|"extra_trigger"|"alt_trigger"|"skip_trigger"} elKey
 * @returns {HTMLElement|null}
 */
function tryFindTrigger(tour, step, elKey) {
    const selector = step[elKey];
    const in_modal = elKey === "extra_trigger" ? false : step.in_modal;
    try {
        const nodes = findTrigger(selector, step.shadow_dom, in_modal);
        //TODO : change _legacyIsVisible by isVisible (hoot lib)
        //Failed with tour test_snippet_popup_with_scrollbar_and_animations > snippet_popup_and_animations
        return !step.allowInvisible && !step.isCheck ? nodes.find(_legacyIsVisible) : nodes.at(0);
    } catch (error) {
        throwError(tour, step, [`Trigger was not found : ${selector} : ${error.message}`]);
    }
}

function findStepTriggers(tour, step) {
    const triggerEl = tryFindTrigger(tour, step, "trigger");
    const altEl = tryFindTrigger(tour, step, "alt_trigger");
    const skipEl = tryFindTrigger(tour, step, "skip_trigger");
    // `extraTriggerOkay` should be true when `step.extra_trigger` is undefined.
    // No need for it to be in the modal.
    const extraTriggerOkay = step.extra_trigger
        ? tryFindTrigger(tour, step, "extra_trigger")
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
function describeFailedStepSimple(tour, step) {
    return `Tour ${tour.name} failed at step ${describeStep(step)}`;
}

function describeWhyStepFailed(step) {
    const stepState = step.state || {};
    if (!stepState.stepElFound) {
        return `The error appears to be that one or more elements in the following list cannot be found in DOM.\n ${JSON.stringify(
            pick(step, "trigger", "extra_trigger", "alt_trigger", "skip_trigger")
        )}`;
    } else if (!stepState.isDisplayed) {
        return "Element has been found but isn't displayed";
    } else if (!stepState.isEnabled) {
        return "Element has been found but is disabled. (Use step.isCheck if you just want to check if element is present in DOM)";
    } else if (stepState.isBlocked) {
        return "Element has been found but DOM is blocked.";
    } else if (!stepState.hasRun) {
        return `Element has been found. The error seems to be in run()`;
    }
    return "";
}

/**
 * @param {TourStep} step
 * @param {Tour} tour
 */
function describeFailedStepDetailed(tour, step) {
    const offset = 3;
    const stepIndex = tour.steps.findIndex((s) => s === step);
    const start = stepIndex - offset >= 0 ? stepIndex - offset : 0;
    const end =
        stepIndex + offset + 1 <= tour.steps.length ? stepIndex + offset + 1 : tour.steps.length;
    let result = [describeFailedStepSimple(tour, step)];
    for (let i = start; i < end; i++) {
        const stepString = JSON.stringify(
            omit(tour.steps[i], "state"),
            (_key, value) => {
                if (typeof value === "function") {
                    return "[function]";
                } else {
                    return value;
                }
            },
            2
        ) + ",";
        const text = [stepString];
        if (i === stepIndex) {
            const line = "-".repeat(10);
            const failing_step = `${line} FAILING STEP (${i + 1}/${tour.steps.length}) ${line}`;
            text.unshift(failing_step);
            text.push("-".repeat(failing_step.length));
        }
        result.push(...text);
    }
    return result.join("\n");
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
    step.state = step.state || {};
    const state = step.state;
    state.stepElFound = true;
    const rootNode = el.getRootNode();
    state.isInDoc =
        rootNode instanceof ShadowRoot
            ? el.ownerDocument.contains(rootNode.host)
            : el.ownerDocument.contains(el);
    state.isElement = el instanceof el.ownerDocument.defaultView.Element || el instanceof Element;
    state.isDisplayed = !step.allowInvisible && !step.isCheck ? isVisible(el) : true;
    const isBlocked =
        document.body.classList.contains("o_ui_blocked") || document.querySelector(".o_blockUI");
    state.isBlocked = !!isBlocked;
    state.isEnabled = !el.disabled || !!step.isCheck;
    state.canContinue = !!(
        state.isInDoc &&
        state.isElement &&
        state.isDisplayed &&
        state.isEnabled &&
        !state.isBlocked
    );
    return state.canContinue;
}

function getStepState(step) {
    const checkRun =
        (["string", "function"].includes(typeof step.run) && step.state.hasRun) ||
        !step.run ||
        step.isCheck;
    const check = checkRun && step.state.canContinue;
    return check ? "succeeded" : "errored";
}

/**
 * @param {TourStep} step
 * @param {Tour} tour
 * @param {Array<string>} [errors]
 */
function throwError(tour, step, errors = []) {
    const debugMode = tourState.get(tour.name, "debug");
    // The logged text shows the relative position of the failed step.
    // Useful for finding the failed step.
    console.warn(describeFailedStepDetailed(tour, step));
    // console.error notifies the test runner that the tour failed.
    console.error(`${describeFailedStepSimple(tour, step)}. ${describeWhyStepFailed(step)}`);
    if (errors.length) {
        console.error(errors.join(", "));
    }
    if (debugMode !== false) {
        // eslint-disable-next-line no-debugger
        debugger;
    }
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

                const { triggerEl, altEl, extraTriggerOkay, skipEl } = findStepTriggers(tour, step);

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
                tourState.set(tour.name, "stepState", getStepState(step));
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
    const { tour, pointer, stepDelay, keepWatchBrowser } = options;
    const { showPointerDuration, onStepConsummed } = options;
    const debugMode = tourState.get(tour.name, "debug");
    let skipAction = false;

    async function tryToDoAction(action) {
        try {
            await action();
            step.state.hasRun = true;
        } catch (error) {
            throwError(tour, step, [error.message]);
        }
    }

    return [
        {
            action: () => {
                setupEventActions(document.createElement("div"));
                step.state = step.state || {};
                if (step.break && debugMode !== false) {
                    // eslint-disable-next-line no-debugger
                    debugger;
                }
            },
        },
        {
            action: async () => {
                // This delay is important for making the current set of tour tests pass.
                // IMPROVEMENT: Find a way to remove this delay.
                await new Promise((resolve) => requestAnimationFrame(resolve));
            },
        },
        {
            action: async () => {
                skipAction = false;
                console.log(`Tour ${tour.name} on step: '${describeStep(step)}'`);
                if (!keepWatchBrowser) {
                    tourTimeout = browser.setTimeout(
                        () => throwError(tour, step),
                        (step.timeout || 10000) + stepDelay
                    );
                }
                await new Promise((resolve) => browser.setTimeout(resolve, stepDelay));
            },
        },
        {
            trigger: () => {
                const { triggerEl, altEl, extraTriggerOkay, skipEl } = findStepTriggers(tour, step);

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
                    step.state.hasRun = true;
                    return;
                }

                if (showPointerDuration > 0) {
                    // Useful in watch mode.
                    pointer.pointTo(stepEl, step);
                    await new Promise((r) => browser.setTimeout(r, showPointerDuration));
                    pointer.hide();
                }

                // TODO: Delegate the following routine to the `ACTION_HELPERS` in the macro module.
                const actionHelper = new RunningTourActionHelper(stepEl);

                let result;
                if (typeof step.run === "function") {
                    const willUnload = await callWithUnloadCheck(async () => {
                        await tryToDoAction(() =>
                            // `this.anchor` is expected in many `step.run`.
                            step.run.call({ anchor: stepEl }, actionHelper)
                        );
                    });
                    result = willUnload && "will unload";
                } else if (typeof step.run === "string") {
                    for (const todo of step.run.split("&&")) {
                        const m = String(todo).trim().match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);
                        await tryToDoAction(() => actionHelper[m.groups?.action](m.groups?.arguments));
                    }
                } else if (!step.isCheck) {
                    if (stepIndex === tour.steps.length - 1) {
                        console.warn("Tour %s: ignoring action (auto) of last step", tour.name);
                        step.state.hasRun = true;
                    } else {
                        await tryToDoAction(() => actionHelper.click());
                    }
                } else {
                    step.state.hasRun = true;
                }

                return result;
            },
        },
        {
            action: () => {
                //Step is passed, timeout can be cleared.
                tourState.set(tour.name, "stepState", getStepState(step));
                browser.clearTimeout(tourTimeout);
                onStepConsummed(tour, step);
            },
        },
        {
            action: async () => {
                if (step.pause && debugMode !== false) {
                    const styles = [
                        "background: black; color: white; font-size: 14px",
                        "background: black; color: orange; font-size: 14px",
                    ];
                    console.log(
                        `%cTour is paused. Use %cplay()%c to continue.`,
                        styles[0],
                        styles[1],
                        styles[0]
                    );
                    window.hoot = hoot;
                    await new Promise((resolve) => {
                        window.play = () => {
                            resolve();
                            delete window.play;
                            delete window.hoot;
                        };
                    });
                }
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
                        clearTimeout(tourTimeout);
                        if (tourState.get(tour.name, "stepState") === "succeeded") {
                            tourState.clear(tour.name);
                            onTourEnd(tour);
                        } else {
                            console.error("tour not succeeded");
                        }
                    },
                },
            ]),
    };
}
