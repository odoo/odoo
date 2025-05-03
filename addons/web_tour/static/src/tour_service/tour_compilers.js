/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { debounce } from "@web/core/utils/timing";
import { _legacyIsVisible, isVisible } from "@web/core/utils/ui";
import { omit } from "@web/core/utils/objects";
import { tourState } from "./tour_state";
import * as hoot from "@odoo/hoot-dom";
import { session } from "@web/session";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { callWithUnloadCheck, getScrollParent } from "./tour_utils";
import { utils } from "@web/core/ui/ui_service";
import { TourHelpers } from "./tour_helpers";
import { isMacOS } from "@web/core/browser/feature_detection";

/**
 * @typedef {import("@web/core/macro").MacroDescriptor} MacroDescriptor
 *
 * @typedef {import("../tour_service/tour_pointer_state").TourPointerState} TourPointerState
 *
 * @typedef {import("./tour_service").TourStep} TourStep
 *
 * @typedef {(stepIndex: number, step: TourStep, options: TourCompilerOptions) => MacroDescriptor[]} TourStepCompiler
 *
 * @typedef {string | (actions: RunningTourActionHelper) => void | Promise<void>} RunCommand
 *
 * @typedef TourCompilerOptions
 * @property {Tour} tour
 * @property {number} stepDelay
 * @property {keepWatchBrowser} boolean
 * @property {showPointerDuration} number
 * @property {*} pointer - used for controlling the pointer of the tour
 *
 * @typedef ConsumeEvent
 * @property {string} name
 * @property {Element} target
 * @property {(ev: Event) => boolean} conditional
 */

/**
 * @param {string} selector - any valid Hoot selector
 * @param {boolean} inModal
 * @returns {Array<Element>}
 */
function findTrigger(selector, inModal) {
    let nodes;
    if (inModal !== false) {
        const visibleModal = hoot.queryAll(".modal", { visible: true }).at(-1);
        if (visibleModal) {
            nodes = hoot.queryAll(selector, { root: visibleModal });
        }
    }
    if (!nodes) {
        nodes = hoot.queryAll(selector);
    }
    return nodes;
}

/**
 * @param {Tour} tour
 * @param {TourStep} step
 * @param {"trigger"|"alt_trigger"} elKey
 * @returns {HTMLElement|null}
 */
function tryFindTrigger(tour, step, elKey) {
    const selector = step[elKey];
    const in_modal = step.in_modal;
    try {
        const nodes = findTrigger(selector, in_modal);
        //TODO : change _legacyIsVisible by isVisible (hoot lib)
        //Failed with tour test_snippet_popup_with_scrollbar_and_animations > snippet_popup_and_animations
        return !step.allowInvisible ? nodes.find(_legacyIsVisible) : nodes.at(0);
    } catch (error) {
        throwError(tour, step, [`Trigger was not found : ${selector} : ${error.message}`]);
    }
}

function findStepTriggers(tour, step) {
    const triggerEl = tryFindTrigger(tour, step, "trigger");
    const altEl = tryFindTrigger(tour, step, "alt_trigger");
    step.state = step.state || {};
    step.state.triggerFound = !!triggerEl;
    step.state.altTriggerFound = !!altEl;
    return { triggerEl, altEl };
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
        return `The cause is that trigger (${step.trigger}) element cannot be found in DOM.`;
    } else if (step.alt_trigger && !stepState.altTriggerFound) {
        return `The cause is that alt(ernative) trigger (${step.alt_trigger}) element cannot be found in DOM.`;
    } else if (!stepState.isVisible) {
        return "Element has been found but isn't displayed. (Use 'step.allowInvisible: true,' if you want to skip this check)";
    } else if (!stepState.isEnabled) {
        return "Element has been found but is disabled.";
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
 * Returns the element that will be used in listening to the `consumeEvent`.
 * @param {HTMLElement} el
 * @param {string} consumeEvent
 */
function getAnchorEl(el, consumeEvent) {
    if (consumeEvent === "drag") {
        // jQuery-ui draggable triggers 'drag' events on the .ui-draggable element,
        // but the tip is attached to the .ui-draggable-handle element which may
        // be one of its children (or the element itself)
        return el.closest(".ui-draggable, .o_draggable, .o_we_draggable, .o-draggable, [draggable='true']");
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
 * Check if a step is active dependant on step.isActive property
 * Note that when step.isActive is not defined, the step is active by default.
 * When a step is not active, it's just skipped and the tour continues to the next step.
 * @param {TourStep} step
 * @param {TourMode} mode TourMode manual means onboarding tour
 */
function isActive(step, mode) {
    const isSmall = utils.isSmall();
    const standardKeyWords = ["enterprise", "community", "mobile", "desktop", "auto", "manual"];
    const isActiveArray = Array.isArray(step.isActive) ? step.isActive : [];
    if (isActiveArray.length === 0) {
        return true;
    }
    const selectors = isActiveArray.filter((key) => !standardKeyWords.includes(key));
    if (selectors.length) {
        // if one of selectors is not found, step is skipped
        for (const selector of selectors) {
            const el = hoot.queryFirst(selector);
            if (!el) {
                return false;
            }
        }
    }
    const checkMode =
        isActiveArray.includes(mode) ||
        (!isActiveArray.includes("manual") && !isActiveArray.includes("auto"));
    const edition = (session.server_version_info || "").at(-1) === "e" ? "enterprise" : "community";
    const checkEdition =
        isActiveArray.includes(edition) ||
        (!isActiveArray.includes("enterprise") && !isActiveArray.includes("community"));
    const onlyForMobile = isActiveArray.includes("mobile") && isSmall;
    const onlyForDesktop = isActiveArray.includes("desktop") && !isSmall;
    const checkDevice =
        onlyForMobile ||
        onlyForDesktop ||
        (!isActiveArray.includes("mobile") && !isActiveArray.includes("desktop"));
    return checkEdition && checkDevice && checkMode;
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
    state.isVisible = step.allowInvisible || isVisible(el);
    const isBlocked =
        document.body.classList.contains("o_ui_blocked") || document.querySelector(".o_blockUI");
    state.isBlocked = !!isBlocked;
    state.isEnabled = step.allowDisabled || !el.disabled;
    state.canContinue = !!(
        state.isInDoc &&
        state.isElement &&
        state.isVisible &&
        state.isEnabled &&
        !state.isBlocked
    );
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

/**
 * @param {Object} params
 * @param {HTMLElement} params.anchorEl
 * @param {import("./tour_utils").ConsumeEvent[]} params.consumeEvents
 * @param {() => void} params.onMouseEnter
 * @param {() => void} params.onMouseLeave
 * @param {(ev: Event) => any} params.onScroll
 * @param {(ev: Event) => any} params.onConsume
 * @param {(ev: Event) => any | undefined} params.onMiss
 */
function setupListeners({
    anchorEl,
    consumeEvents,
    onMouseEnter,
    onMouseLeave,
    onScroll,
    onConsume,
}) {
    let altOnConsume;
    for (const event of consumeEvents) {
        if (event.name === "pointerup") {
            altOnConsume = (ev) => {
                if (document.elementsFromPoint(ev.clientX, ev.clientY).includes(event.target)) {
                    onConsume();
                }
            };
            document.addEventListener(event.name, altOnConsume);
            continue;
        }

        altOnConsume = !event.conditional
            ? onConsume
            : function (ev) {
                  if (event.conditional(ev)) {
                      onConsume();
                  }
              };
        event.target.addEventListener(event.name, altOnConsume, true);
    }
    anchorEl.addEventListener("mouseenter", onMouseEnter);
    anchorEl.addEventListener("mouseleave", onMouseLeave);

    const cleanups = [
        () => {
            for (const event of consumeEvents) {
                if (event.name === "pointerup") {
                    document.removeEventListener(event.name, altOnConsume);
                } else {
                    event.target.removeEventListener(event.name, altOnConsume, true);
                }
            }
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

/**
 *
 * @param {TourStep} step
 * @returns {{
 *  event: string,
 *  anchor: string,
 *  altAnchor: string | undefined,
 * }[]}
 */
function getSubActions(step) {
    const actions = [];
    if (!step.run || typeof step.run === "function") {
        return [];
    }

    for (const todo of step.run.split("&&")) {
        const m = String(todo)
            .trim()
            .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);

        const action = m.groups?.action;
        const anchor = m.groups?.arguments || step.trigger;
        if (action === "drag_and_drop") {
            actions.push({
                event: "drag",
                anchor: step.trigger,
            });
            actions.push({
                event: "drop",
                anchor,
            });
        } else {
            actions.push({
                event: action,
                anchor: action === "edit" ? step.trigger : anchor,
                altAnchor: step.alt_trigger,
            });
        }
    }

    return actions;
}

/**
 * @param {HTMLElement} [element]
 * @param {RunCommand} [runCommand]
 * @returns {ConsumeEvent[]}
 */
function getConsumeEventType(element, runCommand) {
    const consumeEvents = [];
    if (runCommand === "click") {
        consumeEvents.push({
            name: "click",
            target: element,
        });

        // Use the hotkey should also consume
        if (element.hasAttribute("data-hotkey")) {
            consumeEvents.push({
                name: "keydown",
                target: element,
                conditional: (ev) =>
                    ev.key === element.getAttribute("data-hotkey") &&
                    (isMacOS() ? ev.ctrlKey : ev.altKey),
            });
        }

        // Click on a field widget with an autocomplete should be also completed with a selection though Enter or Tab
        // This case is for the steps that click on field_widget
        if (element.querySelector(".o-autocomplete--input")) {
            consumeEvents.push({
                name: "keydown",
                target: element.querySelector(".o-autocomplete--input"),
                conditional: (ev) =>
                    ["Tab", "Enter"].includes(ev.key) &&
                    ev.target.parentElement.querySelector(
                        ".o-autocomplete--dropdown-item .ui-state-active"
                    ),
            });
        }

        // Click on an element of a dropdown should be also completed with a selection though Enter or Tab
        // This case is for the steps that click on a dropdown-item
        if (element.closest(".o-autocomplete--dropdown-menu")) {
            consumeEvents.push({
                name: "keydown",
                target: element.closest(".o-autocomplete").querySelector("input"),
                conditional: (ev) => ["Tab", "Enter"].includes(ev.key),
            });
        }

        // Press enter on a button do the same as a click
        if (element.tagName === "BUTTON") {
            consumeEvents.push({
                name: "keydown",
                target: element,
                conditional: (ev) => ev.key === "Enter",
            });

            // Pressing enter in the input group does the same as clicking on the button
            if (element.closest(".input-group")) {
                for (const inputEl of element.parentElement.querySelectorAll("input")) {
                    consumeEvents.push({
                        name: "keydown",
                        target: inputEl,
                        conditional: (ev) => ev.key === "Enter",
                    });
                }
            }
        }
    }

    if (["fill", "edit"].includes(runCommand)) {
        if (
            utils.isSmall() &&
            element.closest(".o_field_widget")?.matches(".o_field_many2one, .o_field_many2many")
        ) {
            consumeEvents.push({
                name: "click",
                target: element,
            });
        } else {
            consumeEvents.push({
                name: "input",
                target: element,
            });
        }
    }

    // Drag & drop run command
    if (runCommand === "drag") {
        consumeEvents.push({
            name: "pointerdown",
            target: element,
        });
    }

    if (runCommand === "drop") {
        consumeEvents.push({
            name: "pointerup",
            target: element,
        });
    }

    return consumeEvents;
}

/** @type {TourStepCompiler} */
export function compileStepManual(stepIndex, step, options) {
    const { tour, pointer, onStepConsummed } = options;
    let currentSubStep = 0;
    const subSteps = [];
    let anchorEl;
    let removeListeners = () => {};

    const subActions = getSubActions(step);
    if (!subActions.length) {
        return [];
    }

    for (const [subActionIndex, subAction] of subActions.entries()) {
        subSteps.push({
            trigger: () => {
                removeListeners();

                if (!isActive(step, "manual")) {
                    return hoot.queryFirst(".o-main-components-container");
                }

                if (subActionIndex < currentSubStep) {
                    return anchorEl;
                }

                anchorEl = hoot.queryFirst(subAction.anchor);
                const debouncedToggleOpen = debounce(pointer.showContent, 50, true);

                if (anchorEl && canContinue(anchorEl, step)) {
                    anchorEl = getAnchorEl(anchorEl, subAction.event);
                    const consumeEvents = getConsumeEventType(anchorEl, subAction.event);

                    if (subAction.altAnchor) {
                        let altAnchorEl = hoot.queryAll(subAction.altAnchor).at(0);
                        if (altAnchorEl && canContinue(altAnchorEl, step)) {
                            altAnchorEl = getAnchorEl(altAnchorEl, subAction.event);
                            consumeEvents.push(
                                ...getConsumeEventType(altAnchorEl, subAction.event)
                            );
                        }
                    }

                    const updatePointer = () => {
                        pointer.pointTo(anchorEl, step, subAction.event === "drop");

                        pointer.setState({
                            onMouseEnter: () => debouncedToggleOpen(true),
                            onMouseLeave: () => debouncedToggleOpen(false),
                        });
                    };

                    removeListeners = setupListeners({
                        anchorEl,
                        consumeEvents,
                        onMouseEnter: () => pointer.showContent(true),
                        onMouseLeave: () => pointer.showContent(false),
                        onScroll: updatePointer,
                        onConsume: () => {
                            currentSubStep++;
                            pointer.hide();
                        },
                    });

                    updatePointer();
                } else {
                    pointer.hide();
                }
            },
        });
    }

    subSteps.at(-1)["action"] = () => {
        tourState.set(tour.name, "currentIndex", stepIndex + 1);
        tourState.set(tour.name, "stepState", "succeeded");
        pointer.hide();
        currentSubStep = 0;
        onStepConsummed(tour, step);
    };

    return [
        {
            action: () => console.log(step.trigger),
        },
        ...subSteps,
    ];
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
                setupEventActions(document.body);
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
                const { triggerEl, altEl } = findStepTriggers(tour, step);
                const stepEl = triggerEl || altEl;
                if (!stepEl) {
                    return false;
                }

                return canContinue(stepEl, step) && stepEl;
            },
            action: async (stepEl) => {
                //if stepEl is found, timeout can be cleared.
                browser.clearTimeout(tourTimeout);
                tourState.set(tour.name, "currentIndex", stepIndex + 1);

                if (showPointerDuration > 0 && stepEl !== true) {
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
        mode,
        pointer,
        stepDelay,
        keepWatchBrowser,
        showPointerDuration,
        onStepConsummed,
        onTourEnd,
    } = options;
    const currentStepIndex = tourState.get(tour.name, "currentIndex");
    const stepCompiler = mode === "auto" ? compileStepAuto : compileStepManual;
    const checkDelay = mode === "auto" ? tour.checkDelay : 100;

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
