/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { _legacyIsVisible } from "@web/core/utils/ui";
import { omit } from "@web/core/utils/objects";
import { tourState } from "./tour_state";
import * as hoot from "@odoo/hoot-dom";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { callWithUnloadCheck, isActive } from "./tour_utils";
import { TourHelpers } from "./tour_helpers";

/**
 * @typedef {import("@web/core/macro").MacroDescriptor} MacroDescriptor
 *
 * @typedef {import("../tour_service/tour_pointer_state").TourPointerState} TourPointerState
 *
 * @typedef {import("./tour_service").TourStep} TourStep
 *
 * @typedef {(stepIndex: number, step: TourStep, options: TourCompilerOptions) => MacroDescriptor[]} TourStepCompiler
 *
 *
 * @typedef TourCompilerOptions
 * @property {Tour} tour
 * @property {number} stepDelay
 * @property {keepWatchBrowser} boolean
 * @property {showPointerDuration} number
 * @property {*} pointer - used for controlling the pointer of the tour
 *
 */

/**
 * @param {Tour} tour
 * @param {TourStep} step
 * @returns {HTMLElement}
 */
function findTrigger(tour, step) {
    step.state = step.state || {};
    if (!step.trigger) {
        return null;
    }
    const options = {};
    if (step.in_modal !== false) {
        const visibleModal = hoot.queryAll(".modal", { visible: true }).at(-1);
        if (visibleModal) {
            options.root = visibleModal;
        }
    }
    try {
        const nodes = hoot.queryAll(step.trigger, options);
        const triggerEl = step.trigger.includes(":visible")
            ? nodes.at(0)
            : nodes.find(_legacyIsVisible);
        step.state.triggerFound = !!triggerEl;
        return triggerEl;
    } catch (error) {
        throwError(tour, step, [`Trigger was not found : ${step.trigger} : ${error.message}`]);
    }
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
    if (!stepState.triggerFound) {
        return `The cause is that trigger (${step.trigger}) element cannot be found in DOM. TIP: You can use :not(:visible) to force the search for an invisible element.`;
    } else if (stepState.isBlocked) {
        return "Element has been found but DOM is blocked by UI.";
    } else if (!stepState.hasRun) {
        return `Element has been found. The error seems to be with step.run`;
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
    const result = [describeFailedStepSimple(tour, step)];
    for (let i = start; i < end; i++) {
        const stepString =
            JSON.stringify(
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
 * IMPROVEMENT: Consider transitioning (moving) elements?
 * @param {Element} el
 * @param {TourStep} step
 */
function canContinue(el, step) {
    step.state = step.state || {};
    const state = step.state;
    const rootNode = el.getRootNode();
    state.isInDoc =
        rootNode instanceof ShadowRoot
            ? el.ownerDocument.contains(rootNode.host)
            : el.ownerDocument.contains(el);
    state.isElement = el instanceof el.ownerDocument.defaultView.Element || el instanceof Element;
    const isBlocked =
        document.body.classList.contains("o_ui_blocked") || document.querySelector(".o_blockUI");
    state.isBlocked = !!isBlocked;
    state.canContinue = !!(state.isInDoc && state.isElement && !state.isBlocked);
    return state.canContinue;
}

function getStepState(step) {
    step.state = step.state || {};
    const checkRun =
        (["string", "function"].includes(typeof step.run) && step.state.hasRun) || !step.run;
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

let tourTimeout;

/**
 * @type {TourStepCompiler}
 * @param {number} stepIndex
 * @param {TourStep} step
 * @param {object} options
 * @returns {{trigger, action}[]}
 */
export function compileStepAuto(stepIndex, step, options) {
    const { tour, pointer, stepDelay } = options;
    const { showPointerDuration, onStepConsummed } = options;
    const debugMode = tourState.get(tour.name, "debug");

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
                console.log(`Tour ${tour.name} on step: '${describeStep(step)}'`);
                tourTimeout = browser.setTimeout(
                    () => throwError(tour, step),
                    (step.timeout || 10000) + stepDelay
                );
                // This delay is important for making the current set of tour tests pass.
                // IMPROVEMENT: Find a way to remove this delay.
                await new Promise((resolve) => requestAnimationFrame(resolve));
                await new Promise((resolve) => browser.setTimeout(resolve, stepDelay));
            },
        },
        {
            trigger: () => {
                if (!isActive(step, "auto")) {
                    step.run = () => {};
                    step.state.canContinue = true;
                    return true;
                }
                const stepEl = findTrigger(tour, step);
                if (!stepEl) {
                    return false;
                }

                return canContinue(stepEl, step) && stepEl;
            },
            action: async (stepEl) => {
                //if stepEl is found, timeout can be cleared.
                browser.clearTimeout(tourTimeout);
                tourState.set(tour.name, "currentIndex", stepIndex + 1);

                if (showPointerDuration > 0) {
                    // Useful in watch mode.
                    pointer.pointTo(stepEl, step);
                    await new Promise((r) => browser.setTimeout(r, showPointerDuration));
                    pointer.hide();
                }

                // TODO: Delegate the following routine to the `ACTION_HELPERS` in the macro module.
                const actionHelper = new TourHelpers(stepEl);

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
                        const m = String(todo)
                            .trim()
                            .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);
                        await tryToDoAction(() =>
                            actionHelper[m.groups?.action](m.groups?.arguments)
                        );
                    }
                }
                return result;
            },
        },
        {
            action: () => {
                tourState.set(tour.name, "stepState", getStepState(step));
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
        pointer,
        stepDelay,
        keepWatchBrowser,
        showPointerDuration,
        onStepConsummed,
        onTourEnd,
    } = options;
    const currentStepIndex = tourState.get(tour.name, "currentIndex");

    return {
        ...tour,
        steps: filteredSteps
            .reduce((newSteps, step, i) => {
                if (i < currentStepIndex) {
                    // Don't include steps before the current index because they're already done.
                    return newSteps;
                } else {
                    return [
                        ...newSteps,
                        ...compileStepAuto(i, step, {
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
                            onTourEnd(tour);
                        } else {
                            console.error("tour not succeeded");
                        }
                    },
                },
            ]),
    };
}
