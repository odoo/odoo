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
import { iter } from "@web/core/utils/functions";
import { session } from "@web/session";
import { utils } from "@web/core/ui/ui_service";
import { delay } from "@web/core/utils/concurrency";

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
        result += `\n${highlight ? "----- FAILING STEP -----\n" : ""}${stepString},${highlight ? "\n-----------------------" : ""
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

/**
 * @param {TourStep} step
 * @param {Tour} tour
 * @param {Array<string>} [errors]
 */
function throwError(tour, step, errors = []) {
    const debugMode = tourState.get(tour.name, "debug");
    const triggersFound = tourState.get(tour.name, "triggersFound");
    // The logged text shows the relative position of the failed step.
    // Useful for finding the failed step.
    console.warn(describeFailedStepDetailed(tour, step));
    // console.error notifies the test runner that the tour failed.
    console.error(describeFailedStepSimple(tour, step));
    if (triggersFound) {
        console.error(`Triggers have been found. The error seems to be in run()`);
    } else {
        console.error(
            `The error appears to be that one or more items in the following list cannot be found in DOM. : ${JSON.stringify(
                pick(step, "trigger", "extra_trigger", "alt_trigger", "skip_trigger")
            )}`
        );
    }
    if (errors.length) {
        console.error(errors.join(", "));
    }
    tourState.set(tour.name, "hasError", true);
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

export class MacroedTour {
    #tourSteps = [];
    #startIndex = 0;
    #tourTimeout = undefined;
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

    computeSteps() {
        if (this.#tourSteps) {
            return this.#tourSteps;
        }

        let index = 0;
        this.shadowSelectors = new Set();
        this.#tourSteps = this.getTourSteps().map((step, definitionIndex) => {
            const omitted = shouldOmit(step, this.mode);
            const localIndex = !omitted ? index++ : index;
            const completed = localIndex < this.#startIndex;
            step = { ...step, omitted, completed, definitionIndex, index };
            if (!omitted && !completed) {
                step.shadow_dom = step.shadow_dom ?? this.shadow_dom;
                if (step.shadow_dom) {
                    this.shadowSelectors.add(step.shadow_dom);
                }
            }
            return step;
        });
        return this.#tourSteps;
    }

    get tourSteps() {
        return this.computeSteps();
    }

    get steps() {
        return iter(this)
    }

    *[Symbol.iterator]() {
        let compile;
        if (this.mode === "manual") {
            compile = this._compileStepManual.bind(this)
        } else {
            compile = this._compileStepAuto.bind(this)
        }
        for (const tourStep of this.tourSteps) {
            if (tourStep.omitted || tourStep.completed) {
                continue;
            }
            yield* compile(tourStep);
        }
        yield { action: () => {
            if (!tourState.get(this.name, "hasError")) {
                tourState.clear(this.name);
                this.options.pointer.stop();
                this.options.onTourEnd(this);
            } else {
                console.error("tour not succeeded");
            }
        } }
    }

    resetRun(params = {}) {
        Object.assign(this.options, params);
        this.#tourSteps = null;
        if ("startIndex" in params) {
            this.#startIndex = params.startIndex || 0;
        }
        this.computeSteps();
        this.mode = params.mode || this.mode || "auto";
    }

    async tryToDoAction(action, step) {
        try {
            await action();
        } catch (error) {
            throwError(this, step, [error.message]);
        }
    }

    _stepExecute(step, onTriggerEnter=() => {}, onAction=() => {}) {
        let skipAction;
        let enteredCount = 0;
        const trigger = () => {
            onTriggerEnter({ enteredCount });
            enteredCount++;
            skipAction = false;
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
        }
        const action = async (stepEl) => {
            let result;
            if (!skipAction) {
                result = await onAction(stepEl);
            }
            step.completed = true;
            tourState.set(this.name, "currentIndex", step.index + 1);
            this.options.onStepConsummed(this, step);
            return result;
        }
        return { trigger, action };
    }

    /** @type {TourStepCompiler} */
    *_compileStepAuto(step) {
        const { pointer, stepDelay, keepWatchBrowser, showPointerDuration } =
            this.options;
        const debugMode = tourState.get(this.name, "debug");

        const delayToAction = (step.timeout || 10000) + stepDelay;
        let timeout;
        const onTriggerEnter = ({enteredCount}) => {
            if (!enteredCount) {
                console.log(`Tour ${this.name} on step: '${describeStep(step)}'`);
                tourState.set(this.name, "triggersFound", false);
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
        }
        const onAction = async (stepEl) => {
            clearTimeout(timeout);
            tourState.set(this.name, "triggersFound", true);
            if (showPointerDuration > 0) {
                // Useful in watch mode.
                pointer.pointTo(stepEl, step);
                await new Promise((r) => browser.setTimeout(r, showPointerDuration));
                pointer.hide();
            }
            return this._autoRunStep(step, stepEl);
        }

        yield this._stepExecute(step, onTriggerEnter, onAction);
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
                    step.run.call({ anchor: stepEl }, actionHelper)
                );
            });
            result = willUnload && "will unload";
        } else if (step.run !== undefined) {
            const m = step.run.match(/^([a-zA-Z0-9_]+) *(?:\(? *(.+?) *\)?)?$/);
            await tryToDoAction(() => actionHelper[m[1]](m[2]));
        } else if (!step.isCheck) {
            if (stepIndex === tour.steps.length - 1) {
                console.warn('Tour %s: ignoring action (auto) of last step', tour.name);
            } else {
                await tryToDoAction(() => actionHelper.auto());
            }
        }
        await new Promise(r => delay(0).then(() => requestAnimationFrame(r)));
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
    _compileStepManual(step) {
        const tour = this.tour;
        const stepIndex = step.index;
        const { pointer, onStepConsummed } = this.options;
        let proceedWith = null;
        let removeListeners = () => { };
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
                        const consumeEvent =
                            step.consumeEvent || getConsumeEventType(stepEl, step.run);
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
                    step.completed = true;
                    tourState.set(this.name, "currentIndex", stepIndex + 1);
                    pointer.hide();
                    proceedWith = null;
                    onStepConsummed(tour, step);
                },
            },
        ];
    }
}

