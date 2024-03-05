/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { debounce } from "@web/core/utils/timing";
import { _legacyIsVisible, isVisible } from "@web/core/utils/ui";
import { tourState } from "./tour_state";
import {
    callWithUnloadCheck,
    getConsumeEventType,
    getNodesFromSelector,
    getScrollParent,
    RunningTourActionHelper,
} from "./tour_utils";
import { session } from "@web/session";
import { utils } from "@web/core/ui/ui_service";
import { Deferred, delay } from "@web/core/utils/concurrency";
import { rangeAround } from "@web/core/utils/arrays";
import { queryAll } from "@odoo/hoot-dom";
import { pick } from "@web/core/utils/objects";

/**
 * @typedef {import("@web/core/macro").MacroDescriptor} MacroDescriptor
 *
 * @typedef {import("./tour_pointer_state").TourPointerState} TourPointerState
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
        const visibleModal = queryAll(".modal", { root: target, visible: true }).at(-1);
        if (visibleModal) {
            nodes = queryAll(selector, { root: visibleModal });
        }
    }
    if (!nodes) {
        nodes = getNodesFromSelector(selector, target);
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

/**
 * @param {TourStep} step
 * @param {Tour} tour
 */
function describeFailedStepDetailed(tour, step) {
    let result = "";
    for (const elem of rangeAround(tour.tourSteps, step.index, 3)) {
        const highlight = elem === step;
        const stepString = JSON.stringify(
            elem,
            (_key, value) => {
                if (typeof value === "function") {
                    return "[function]";
                } else {
                    return value;
                }
            },
            2
        );
        result += `\n${highlight ? "----- FAILING STEP -----\n" : ""}${stepString},${highlight ? "\n-----------------------" : ""}`;
    }
    return `${describeFailedStepSimple(tour, step)}\n\n${result.trim()}`;
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
    console.error(describeFailedStepSimple(tour, step));
    console.error(describeWhyStepFailed(step));
    if (errors.length) {
        console.error(errors.join(", "));
    }
    if (debugMode !== false) {
        // eslint-disable-next-line no-debugger
        debugger;
    }
}

const isKeyDefined = (key, obj) => key in obj && obj[key] !== undefined;
const odooEdition = (session.server_version_info || []).at(-1) === "e" ? "enterprise" : "community";

function shouldOmit(step, mode) {
    const correctEdition = isKeyDefined("edition", step)
        ? step.edition === odooEdition
        : true;
    const correctDevice = isKeyDefined("mobile", step) ? step.mobile === utils.isSmall() : true;
    return (
        !correctEdition ||
        !correctDevice ||
        // `step.auto = true` means omitting a step in a manual tour.
        (mode === "manual" && step.auto)
    );
}

export async function animationFrame() {
    await new Promise((resolve) => requestAnimationFrame(resolve));
    await delay(0);
}

export class MacroedTour {
    _tourSteps = [];
    _startIndex = 0;
    constructor(tour, options={}) {
        if (typeof tour.steps !== "function") {
            throw new Error(`tour.steps has to be a function that returns TourStep[]`);
        }
        this.getTourSteps = tour.steps;
        tour = { ...tour };
        delete tour.steps;
        Object.assign(this, tour);
        this.options = {};
        this.resetRun(options);

    }

    computeSteps(reset=false) {
        if (this._tourSteps && !reset) {
            return this._tourSteps;
        }
        let index = 0;
        this.shadowSelectors = new Set();

        const allSteps = [];
        const tourSteps = [];
        this.getTourSteps().forEach((step, definitionIndex) => {
            const omitted = shouldOmit(step, this.mode);
            step = { ...step, definitionIndex };
            allSteps.push(step);
            if (!omitted) {
                step.index = index;
                const completed = index < this._startIndex;
                if (!completed) {
                    step.shadow_dom = step.shadow_dom ?? this.shadow_dom;
                    if (step.shadow_dom) {
                        this.shadowSelectors.add(step.shadow_dom);
                    }
                    tourSteps.push(step);
                }
                index++;
            }
        });
        this._allSteps = allSteps;
        this._tourSteps = tourSteps;
        return this._tourSteps;
    }

    get tourSteps() {
        return this.computeSteps();
    }

    get steps() {
        return this[Symbol.iterator]();
    }

    *[Symbol.iterator]() {
        let compile;
        if (this.mode === "manual") {
            compile = this._compileStepManual.bind(this)
        } else {
            compile = this._compileStepAuto.bind(this)
        }

        for (const tourStep of this.tourSteps) {
            if (tourStep.completed) {
                continue;
            }
            yield* compile(tourStep);
        }

        yield { action: () => {
                if (tourState.get(this.name, "stepState") === "succeeded") {
                    tourState.clear(this.name);
                    this.options.onTourEnd(this);
                } else {
                    console.error("tour not succeeded");
                }
            } 
        }
        this._tourSteps = null;
    }

    resetRun(params = {}) {
        Object.assign(this.options, params);
        if ("startIndex" in params) {
            this._startIndex = params.startIndex || 0;
        }
        this.computeSteps(true);
        this.mode = params.mode || this.mode || "auto";
    }

    async tryToDoAction(action, step) {
        try {
            await action();
            step.state.hasRun = true;
        } catch (error) {
            throwError(this, step, [error.message]);
        }
    }

    _stepTriggered(step) {
        const { triggerEl, altEl, extraTriggerOkay, skipEl } = findStepTriggers(this, step);
        const stepEl = extraTriggerOkay && (triggerEl || altEl);

        if (skipEl) {
            return {
                element: skipEl,
                shouldSkipAction: true,
            };
        }

        if (!stepEl || !canContinue(stepEl, step)) {
            return { element: null };
        }
        return { element: stepEl };
    }

    _markStepComplete(step) {
        step.completed = true;
        step.state.hasRun = true;
        tourState.set(this.name, "currentIndex", step.index + 1);
        tourState.set(this.name, "stepState", getStepState(step));
        this.options.onStepConsummed(this, step);
    }

    /** @type {TourStepCompiler} */
    *_compileStepAuto(step) {
        const { pointer, stepDelay, keepWatchBrowser, showPointerDuration } =
            this.options;
        const debugMode = tourState.get(this.name, "debug");

        const delayToAction = (step.timeout || 10000) + stepDelay;
        let timeout;

        let enteredCount = 0;
        let shouldDoAction = false;
        debugger;
        const trigger = () => {
            debugger;
            step.state = step.state || {};
            if (!enteredCount) {
                console.log(`Tour ${this.name} on step: '${describeStep(step)}'`);
                if (step.break && debugMode !== false) {
                    // eslint-disable-next-line no-debugger
                    debugger;
                }
            }
            if (!keepWatchBrowser && !enteredCount) {
                timeout = setTimeout(() => {
                    throwError(this, step)
                }, delayToAction)
            }
            const { element, shouldSkipAction } = this._stepTriggered(step);
            shouldDoAction = !shouldSkipAction;

            enteredCount++;
            return element;
        }

        const action = async (stepEl) => {
            clearTimeout(timeout);
            if (!shouldDoAction) {
                this._markStepComplete(step);
                return;
            }
            if (showPointerDuration > 0) {
                // Useful in watch mode.
                pointer.pointTo(stepEl, step);
                await new Promise((r) => browser.setTimeout(r, showPointerDuration));
                pointer.hide();
            }
            const result = await this._autoRunStep(step, stepEl);
            this._markStepComplete(step);
            await animationFrame();
            return result;
        }
        yield { trigger, action };

        if (step.pause && debugMode !== false) {
            yield { action: this._actionPause.bind(this) }
        }
    }

    async _autoRunStep(step, stepEl) {
        const consumeEvent = step.consumeEvent || getConsumeEventType(stepEl, step.run);
        // TODO: Delegate the following routine to the `ACTION_HELPERS` in the macro module.
        const actionHelper = new RunningTourActionHelper({
            consume_event: consumeEvent,
            anchor: stepEl,
        });

        let result;
        if (typeof step.run === "function") {
            const willUnload = await callWithUnloadCheck(async () => {
                await this.tryToDoAction(() =>
                    // `this.anchor` is expected in many `step.run`.
                    step.run.call({ anchor: stepEl }, actionHelper), step
                );
            });
            result = willUnload && "will unload";
        } else if (step.run !== undefined) {
            const m = step.run.match(/^([a-zA-Z0-9_]+) *(?:\(? *(.+?) *\)?)?$/);
            await this.tryToDoAction(() => actionHelper[m[1]](m[2]), step);
        } else if (!step.isCheck) {
            if (step.index === this.tourSteps.length - 1) {
                console.warn('Tour %s: ignoring action (auto) of last step', this.name);
            } else {
                await this.tryToDoAction(() => actionHelper.auto(), step);
            }
        }
        await delay(0);
        return result;
    }

    _actionPause() {
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
        return new Promise((resolve) => {
            window.play = () => {
                resolve();
                delete window.play;
            };
        });
    }

    /** @type {TourStepCompiler} */
    *_compileStepManual(step) {
        let removeListeners;

        const { pointer } = this.options;
        const debouncedToggleOpen = debounce(pointer.showContent, 50, true);

        const updatePointer = (anchorEl) => {
            pointer.setState({
                onMouseEnter: () => debouncedToggleOpen(true),
                onMouseLeave: () => debouncedToggleOpen(false),
            });
            pointer.pointTo(anchorEl, step);
        };
        const onConsume = () => {
            pointer.hide();
            removeListeners();
        }

        let enteredCount = 0;
        const trigger = () => {
            removeListeners && removeListeners();
            if (!enteredCount) {
                console.log(step.trigger);
            }
            enteredCount++;

            const { element, shouldSkipAction } = this._stepTriggered(step);
            if (!element || shouldSkipAction) {
                pointer.hide();
                return shouldSkipAction && element;
            }
            const stepEl = element;
            const consumeEvent = step.consumeEvent || getConsumeEventType(stepEl, step.run);
            const anchorEl = getAnchorEl(stepEl, consumeEvent);

            let consumed = false; 
            removeListeners = setupListeners({
                anchorEl,
                consumeEvent,
                onMouseEnter: () => pointer.showContent(true),
                onMouseLeave: () => pointer.showContent(false),
                onScroll: () => updatePointer(anchorEl),
                onConsume: () => {
                    consumed = true;
                    onConsume();
                },
            });
            updatePointer(stepEl);
            return consumed && stepEl;
        }

        yield { trigger, action: this._markStepComplete.bind(this, step)}
    }
}

