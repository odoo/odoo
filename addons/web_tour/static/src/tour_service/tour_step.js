import * as hoot from "@odoo/hoot-dom";
import { omit } from "@web/core/utils/objects";
import { tourState } from "./tour_state";
import { debounce } from "@web/core/utils/timing";
import { validate } from "@odoo/owl";
import { callWithUnloadCheck, getScrollParent } from "./tour_utils";
import { utils } from "@web/core/ui/ui_service";
import { setupEventActions } from "@web/../lib/hoot-dom/helpers/events";
import { browser } from "@web/core/browser/browser";
import { TourHelpers } from "./tour_helpers";
import { session } from "@web/session";
import { _legacyIsVisible, isVisible } from "@web/core/utils/ui";

const schema = {
    id: { type: String, optional: true },
    trigger: { type: String },
    alt_trigger: { type: String, optional: true },
    isActive: { type: Array, element: String, optional: true },
    content: { type: [String, Object], optional: true }, //allow object for _t && markup
    position: { type: String, optional: true },
    run: { type: [String, Function], optional: true },
    allowInvisible: { type: Boolean, optional: true },
    allowDisabled: { type: Boolean, optional: true },
    in_modal: { type: Boolean, optional: true },
    timeout: { type: Number, optional: true },
    consumeEvent: { type: String, optional: true },
    title: { type: String, optional: true },
    debugHelp: { type: String, optional: true },
    noPrepend: { type: Boolean, optional: true },
    pause: { type: Boolean, optional: true }, //ONLY IN DEBUG MODE
    break: { type: Boolean, optional: true }, //ONLY IN DEBUG MODE
};

export class TourStep {
    tour = "";
    content = "";
    element = null;
    state = {};
    stepDelay;
    keepWatchBrowser;
    showPointerDuration;

    constructor(data, tour) {
        if (!tour) {
            throw new Error(`StepTour instance must have a tour !`);
        }
        this.tour = tour;
        this.validateSchema(data);
        return this;
    }

    get canContinue() {
        const rootNode = this.element.getRootNode();
        this.state.isInDoc =
            rootNode instanceof ShadowRoot
                ? this.element.ownerDocument.contains(rootNode.host)
                : this.element.ownerDocument.contains(this.element);
        this.state.isElement =
            this.element instanceof this.element.ownerDocument.defaultView.Element ||
            this.element instanceof Element;
        this.state.isVisible = this.allowInvisible || isVisible(this.element);
        const isBlocked =
            document.body.classList.contains("o_ui_blocked") ||
            document.querySelector(".o_blockUI");
        this.state.isBlocked = !!isBlocked;
        this.state.isEnabled = this.allowDisabled || !this.element.disabled;
        this.state.canContinue = !!(
            this.state.isInDoc &&
            this.state.isElement &&
            this.state.isVisible &&
            this.state.isEnabled &&
            !this.state.isBlocked
        );
        return this.state.canContinue;
    }

    get anchorElement() {
        if (this.consumeEvent === "drag") {
            // jQuery-ui draggable triggers 'drag' events on the .ui-draggable element,
            // but the tip is attached to the .ui-draggable-handle element which may
            // be one of its children (or the element itself)
            return this.element.closest(".ui-draggable, .o_draggable");
        }
        if (
            this.consumeEvent === "input" &&
            !["textarea", "input"].includes(this.element.tagName.toLowerCase())
        ) {
            return this.element.closest("[contenteditable='true']");
        }
        if (this.consumeEvent === "sort") {
            // when an element is dragged inside a sortable container (with classname
            // 'ui-sortable'), jQuery triggers the 'sort' event on the container
            return this.element.closest(".ui-sortable, .o_sortable");
        }
        return this.element;
    }

    compileToMacro(pointer) {
        const mode = tourState.get(this.tour.name, "mode");
        return mode === "manual"
            ? this._compileToMacroManualMode(pointer)
            : this._compileToMacroAutoMode(pointer);
    }

    get consumeEventType() {
        if (!this.element) {
            return "click";
        }
        const { classList, tagName, type } = this.element;
        const tag = tagName.toLowerCase();
        // Many2one
        if (classList.contains("o_field_many2one")) {
            return "autocompleteselect";
        }
        // Inputs and textareas
        if (
            tag === "textarea" ||
            (tag === "input" &&
                (!type ||
                    [
                        "email",
                        "number",
                        "password",
                        "search",
                        "tel",
                        "text",
                        "url",
                        "date",
                        "range",
                    ].includes(type)))
        ) {
            if (
                utils.isSmall() &&
                this.element
                    .closest(".o_field_widget")
                    ?.matches(".o_field_many2one, .o_field_many2many")
            ) {
                return "click";
            }
            return "input";
        }

        // Drag & drop run command
        if (typeof this.run === "string" && /^drag_and_drop/.test(this.run)) {
            // this is a heuristic: the element has to be dragged and dropped but it
            // doesn't have class 'ui-draggable-handle', so we check if it has an
            // ui-sortable parent, and if so, we conclude that its event type is 'sort'
            if (this.element.closest(".ui-sortable")) {
                return "sort";
            }
            if (
                (/^drag_and_drop_native/.test(this.run) && classList.contains("o_draggable")) ||
                this.element.closest(".o_draggable") ||
                this.element.draggable
            ) {
                return "pointerdown";
            }
        }

        // Default: click
        return "click";
    }

    /**
     * @param {TourStep} step
     * @param {Tour} tour
     */
    get describeFailedDetailed() {
        const steps = this.tour.steps;
        const offset = 3;
        const start = Math.max(this.index - offset, 0);
        const end = Math.min(this.index + offset, steps.length);
        const result = [];
        for (let i = start; i <= end; i++) {
            const stepString =
                JSON.stringify(
                    omit(steps[i], "state"),
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
            if (i === this.index) {
                const line = "-".repeat(10);
                const failing_step = `${line} ${this.describeMe} ${line}`;
                text.unshift(failing_step);
                text.push("-".repeat(failing_step.length));
            }
            result.push(...text);
        }
        return result.join("\n");
    }

    get describeMe() {
        return `Tour ${this.tour.name} at Step (${this.index + 1} / ${this.tour.steps.length}): ${
            this.content ? `${this.content} (trigger: ${this.trigger})` : this.trigger
        }`;
    }

    get describeWhyFailed() {
        if (!this.state.triggerFound) {
            return `The cause is that trigger (${this.trigger}) element cannot be found in DOM.`;
        } else if (this.alt_trigger && !this.state.altTriggerFound) {
            return `The cause is that alt(ernative) trigger (${this.alt_trigger}) element cannot be found in DOM.`;
        } else if (!this.state.isVisible) {
            return "Element has been found but isn't displayed. (Use 'step.allowInvisible: true,' if you want to skip this check)";
        } else if (!this.state.isEnabled) {
            return "Element has been found but is disabled.";
        } else if (this.state.isBlocked) {
            return "Element has been found but DOM is blocked by UI.";
        } else if (!this.state.hasRun) {
            return `Element has been found. The error seems to be with step.run`;
        }
        return "";
    }

    /**
     * @param {string} selector - any valid Hoot selector
     * @param {boolean} inModal
     * @returns {Array<Element>}
     */
    findTrigger(selector, inModal) {
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

    findTriggers() {
        const triggerEl = this.tryFindTrigger("trigger");
        const altEl = this.tryFindTrigger("alt_trigger");
        this.state = this.state || {};
        this.state.triggerFound = !!triggerEl;
        this.state.altTriggerFound = !!altEl;
        return { triggerEl, altEl };
    }

    /**
     * Check if a step is active dependant on step.isActive property
     * Note that when step.isActive is not defined, the step is active by default.
     * When a step is not active, it's just skipped and the tour continues to the next step.
     */
    get imActive() {
        const isSmall = utils.isSmall();
        const standardKeyWords = ["enterprise", "community", "mobile", "desktop", "auto", "manual"];
        const isActiveArray = Array.isArray(this.isActive) ? this.isActive : [];
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
        const mode = tourState.get(this.tour.name, "mode");
        const checkMode =
            isActiveArray.includes(mode) ||
            (!isActiveArray.includes("manual") && !isActiveArray.includes("auto"));
        const edition =
            (session.server_version_info || "").at(-1) === "e" ? "enterprise" : "community";
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
     * @param {Object} params
     * @param {HTMLElement} params.anchorEl
     * @param {string} params.consumeEvent
     * @param {() => void} params.onMouseEnter
     * @param {() => void} params.onMouseLeave
     * @param {(ev: Event) => any} params.onScroll
     * @param {(ev: Event) => any} params.onConsume
     */
    setupListeners({ onMouseEnter, onMouseLeave, onScroll, onConsume }) {
        this.anchorElement.addEventListener(this.consumeEvent, onConsume);
        this.anchorElement.addEventListener("mouseenter", onMouseEnter);
        this.anchorElement.addEventListener("mouseleave", onMouseLeave);

        const cleanups = [
            () => {
                this.anchorElement.removeEventListener(this.consumeEvent, onConsume);
                this.anchorElement.removeEventListener("mouseenter", onMouseEnter);
                this.anchorElement.removeEventListener("mouseleave", onMouseLeave);
            },
        ];

        const scrollEl = getScrollParent(this.anchorElement);
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
    throwError(errors = []) {
        tourState.set(this.tour.name, "tourState", "errored");
        console.warn(this.describeFailedDetailed);
        console.error(`${this.describeMe}\n${this.describeWhyFailed}`);
        if (errors.length) {
            console.error(errors.join(", "));
        }
        if (tourState.get(this.tour.name, "debug") !== false) {
            // eslint-disable-next-line no-debugger
            debugger;
        }
    }

    tryFindTrigger(elKey) {
        const selector = this[elKey];
        const in_modal = this.in_modal;
        try {
            const nodes = this.findTrigger(selector, in_modal);
            //TODO : change _legacyIsVisible by isVisible (hoot lib)
            //Failed with tour test_snippet_popup_with_scrollbar_and_animations > snippet_popup_and_animations
            return !this.allowInvisible ? nodes.find(_legacyIsVisible) : nodes.at(0);
        } catch (error) {
            this.throwError([`Trigger was not found : ${selector} : ${error.message}`]);
        }
    }

    async tryToDoAction(action) {
        try {
            await action();
            this.state.hasRun = true;
        } catch (error) {
            this.throwError([error.message]);
        }
    }

    validateSchema(data) {
        try {
            validate(data, schema);
            Object.assign(this, data);
            return true;
        } catch (error) {
            console.error(`Error for step ${JSON.stringify(data, null, 4)}\n${error.message}`);
            return false;
        }
    }

    _compileToMacroAutoMode(pointer) {
        const debugMode = tourState.get(this.tour.name, "debug");
        return [
            {
                action: async () => {
                    // TODO: ensure the clipboard works
                    setupEventActions(document.createElement("div"));
                    console.log(this.describeMe);
                    if (debugMode !== false && this.break) {
                        // eslint-disable-next-line no-debugger
                        debugger;
                    }
                    //TODO: Use waitFor instead of a setTimeout
                    this.tour.timeout = browser.setTimeout(
                        () => this.throwError(),
                        (this.timeout || 10000) + this.stepDelay
                    );
                    // This delay is important for making the current set of tour tests pass.
                    // IMPROVEMENT: Find a way to remove this delay.
                    await new Promise((resolve) => requestAnimationFrame(resolve));
                    await new Promise((resolve) => browser.setTimeout(resolve, this.stepDelay));
                },
            },
            {
                trigger: () => {
                    if (!this.imActive) {
                        this.run = () => {};
                        this.state.canContinue = true;
                        return true;
                    }
                    const { triggerEl, altEl } = this.findTriggers();
                    this.element = triggerEl || altEl;
                    if (!this.element) {
                        return false;
                    }

                    return this.canContinue && this.element;
                },
                action: async () => {
                    browser.clearTimeout(this.tour.timeout);
                    tourState.set(this.tour.name, "currentIndex", this.index + 1);
                    if (this.showPointerDuration > 0) {
                        // Useful in watch mode.
                        pointer.pointTo(this.element, this);
                        await new Promise((r) => browser.setTimeout(r, this.showPointerDuration));
                        pointer.hide();
                    }

                    // TODO: Delegate the following routine to the `ACTION_HELPERS` in the macro module.
                    const helpers = new TourHelpers(this.element);

                    let result;
                    if (typeof this.run === "function") {
                        const willUnload = await callWithUnloadCheck(async () => {
                            await this.tryToDoAction(() =>
                                // `this.anchor` is expected in many `step.run`.
                                this.run.call({ anchor: this.element }, helpers)
                            );
                        });
                        result = willUnload && "will unload";
                    } else if (typeof this.run === "string") {
                        for (const todo of this.run.split("&&")) {
                            const m = String(todo)
                                .trim()
                                .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);
                            await this.tryToDoAction(() =>
                                helpers[m.groups?.action](m.groups?.arguments)
                            );
                        }
                    }
                    return result;
                },
            },
            {
                action: async () => {
                    if (this.pause && debugMode !== false) {
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

    _compileToMacroManualMode(pointer) {
        let proceedWith = null;
        let removeListeners = () => {};
        return [
            {
                action: () => {
                    console.log(this.describeMe);
                },
            },
            {
                trigger: () => {
                    removeListeners();
                    if (!this.imActive) {
                        return true;
                    }
                    if (proceedWith) {
                        return proceedWith;
                    }

                    const { triggerEl, altEl } = this.findTriggers();

                    this.element = triggerEl || altEl;

                    if (this.element && this.canContinue) {
                        this.consumeEvent = this.consumeEvent || this.consumeEventType;
                        const debouncedToggleOpen = debounce(pointer.showContent, 50, true);

                        const updatePointer = () => {
                            pointer.setState({
                                onMouseEnter: () => debouncedToggleOpen(true),
                                onMouseLeave: () => debouncedToggleOpen(false),
                            });
                            pointer.pointTo(this.anchorElement, this);
                        };

                        removeListeners = this.setupListeners({
                            onMouseEnter: () => pointer.showContent(true),
                            onMouseLeave: () => pointer.showContent(false),
                            onScroll: updatePointer,
                            onConsume: () => {
                                proceedWith = this.element;
                                pointer.hide();
                            },
                        });

                        updatePointer();
                    } else {
                        pointer.hide();
                    }
                },
                action: () => {
                    tourState.set(this.tour.name, "currentIndex", this.index + 1);
                    pointer.hide();
                    proceedWith = null;
                },
            },
        ];
    }
}
