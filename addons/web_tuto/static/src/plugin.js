import {
    onWillDestroy,
    onWillStart,
    Plugin,
    t,
    useListener,
    usePlugin,
    whenReady,
} from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { EffectPlugin } from "@web/core/effects/effect_plugin";
import { _t } from "@web/core/l10n/translation";
import { rpcBus } from "@web/core/network/rpc";
import { ORM } from "@web/core/orm_plugin";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { useDebounced, useThrottleForAnimation } from "@web/core/utils/timing";
import { session } from "@web/session";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";
import { dialogViews } from "@web_tuto/displayed_views";
import { TutorialPointer } from "@web_tuto/pointer/pointer";
import { pointerState } from "@web_tuto/pointer/pointer_state";

/**
 * The chapters of the tutorials, by name of their `web_tuto.tutorial`
 * record. A chapter is a view, with its steps:
 * - a field step (`type: "field"`) names a field of the view (e.g.
 *   `partner_id`, or `order_line.product_id` for a field of the lines of a
 *   x2many field), done once focused;
 * - an action step (`type: "action"`) is an action on the element of its
 *   `trigger` (a selector), done once the user did it, or Next did it for
 *   them: `click` it, `drag` it, or `drop` onto it the element dragged by
 *   the previous step (a drag being always followed by its drop).
 * A hint (`hint: true`) is only shown, the user going on with Next.
 *
 * @typedef {Object} TutorialChapterDefinition
 * @property {string} model
 * @property {TutorialStepDefinition[]} steps
 * @property {string} viewType e.g. "form"; a list or kanban chapter is shown
 *   in any view of several records of its model
 *
 * @typedef {Object} TutorialStepDefinition
 * @property {"click"|"drag"|"drop"} [action]
 * @property {string} content the help shown by the pointer
 * @property {boolean} [hint]
 * @property {string} [name]
 * @property {"bottom"|"left"|"right"|"top"} [tooltipPosition]
 * @property {string} [trigger]
 * @property {"action"|"field"} type
 */

/** A step: a field step needs its `name`, an action step its `action` and `trigger` */
const stepSchema = t.customValidator(
    t.strictObject({
        action: t.selection(["click", "drag", "drop"]).optional(),
        content: t.string(),
        hint: t.boolean().optional(),
        name: t.string().optional(),
        tooltipPosition: t.selection(["bottom", "left", "right", "top"]).optional(),
        trigger: t.string().optional(),
        type: t.selection(["action", "field"]),
    }),
    (step) => (step.type === "field" ? Boolean(step.name) : Boolean(step.action && step.trigger)),
    "a field step needs its name, an action step its action and trigger"
);

export const tutorialSchema = t.array(
    t.strictObject({
        model: t.string(),
        steps: t.customValidator(
            t.array(stepSchema),
            (steps) =>
                steps.every(
                    (step, index) =>
                        (step.action === "drag") === (steps[index + 1]?.action === "drop") &&
                        (step.action === "drop") === (steps[index - 1]?.action === "drag")
                ),
            "a drag step is followed by its drop step, and a drop step follows its drag step"
        ),
        viewType: t.customValidator(t.string(), (viewType) => viewType in session.view_info),
    })
);

registry.category("web_tuto.tutorials").addValidation(tutorialSchema);

/**
 * @param {TutorialChapterDefinition[]} chapters
 * @returns {string[][]} the keys of the steps by chapter, saving the progress
 *   of the user: its view and its field or trigger, numbered from the second
 *   step with the same ones (e.g. `"crm.lead,kanban,name"`)
 */
export function getStepKeys(chapters) {
    const counts = new Map();
    return chapters.map(({ model, steps, viewType }) =>
        steps.map((step) => {
            const key = [model, viewType, step.type === "field" ? step.name : step.trigger].join();
            const count = (counts.get(key) || 0) + 1;
            counts.set(key, count);
            return count > 1 ? `${key},${count}` : key;
        })
    );
}

/** How far the pointer pressed on an element moves to drag it, in pixels */
const DRAG_DISTANCE = 5;

/** @type {Partial<TutorialPointerState>} the pointer showing nothing */
const HIDDEN_POINTER = {
    alwaysOpen: false,
    content: "",
    invalid: false,
    onNext: undefined,
    progress: "",
    side: "bottom",
    trigger: undefined,
};

/**
 * Guides the user through the running tutorials. A chapter is a view with
 * its steps (a list chapter is also shown in the other views of its model).
 * In the displayed chapter, the pointer shows the first step not done yet,
 * done by the user or with Next. A tutorial goes on from its last chapter
 * with a done step, and is finished with the steps of its last chapter.
 *
 * - When no remaining step can be done (e.g. the record failed to be saved),
 *   the pointer goes back to the last done step, doing it again resetting
 *   the steps after it; never while an RPC is pending (the next view may be
 *   loading).
 * - An invalid field (e.g. a required one) is pointed first.
 * - The pointer hides while its trigger is covered (e.g. by a dropdown).
 * - The URL of the view with a step to do is saved, to resume there.
 */
export class TutorialPlugin extends Plugin {
    action = usePlugin(ActionPlugin);
    /**
     * The DOM helpers of the tutorials (`@web_tuto/tutorial/utils`), in the
     * bundle only loaded once some tutorials run
     */
    domUtils = null;
    /**
     * The element the user pressed the pointer on, which they may drag, and
     * where
     * @type {{ source: Element, x: number, y: number } | null}
     */
    dragStart = null;
    effect = usePlugin(EffectPlugin);
    /** Whether the plugin is destroyed, e.g. before its bootstrap ended */
    isDestroyed = false;
    /**
     * Whether the user is pressing a pointer or a key, an autofocus not doing
     * a field step
     */
    isUserInteracting = false;
    /** @type {TourInteractiveObserver | null} */
    observer = null;
    /**
     * Does the pointed step once no RPC is pending (e.g. a kanban view being
     * reloaded), unless the user left its view or did it meanwhile. An action
     * is marked done by its events (e.g. its click), as when the user does it.
     */
    onNext = async () => {
        const step = this.pointedStep;
        if (!step) {
            return;
        }
        await this._waitForRpcs();
        const root = this.domUtils.getRoot();
        const isViewLeft = !this._getDisplayedSteps(root).includes(step);
        const isDoneByUserMeanwhile = step.done && step !== this.pointedStep;
        if (isViewLeft || isDoneByUserMeanwhile) {
            return;
        }
        if (step.type === "field" || step.hint) {
            this._markDone([step]);
        }
        step.perform(root);
    };
    onSkip = () => this.pointedStep && this.endTutorial(this.pointedStep.tutorial);
    orm = usePlugin(ORM);
    overlay = usePlugin(OverlayPlugin);
    /** The ids of the pending RPCs, during which the pointer doesn't go back */
    pendingRpcIds = new Set();
    /**
     * The step the pointer shows, which may be a done step to do again
     * @type {TutorialStep | null}
     */
    pointedStep = null;
    /** The callbacks to call once no RPC is pending anymore */
    rpcsDoneCallbacks = [];
    tutorials = [];

    /** Starts the running tutorials without delaying the web client */
    setup() {
        onWillStart(() => {
            this._bootstrap();
        });
        useListener(document, "click", (ev) => this._onClick(ev), {
            capture: true,
        });
        useListener(document, "focusin", (ev) => this._markFieldDoneBy(ev.target), {
            capture: true,
        });
        useListener(document, "pointerdown", (ev) => this._onPointerDown(ev), {
            capture: true,
        });
        useListener(document, "pointermove", (ev) => this._onPointerMove(ev), {
            capture: true,
        });
        useListener(document, "pointerup", (ev) => this._onPointerUp(ev), {
            capture: true,
        });
        useListener(document, "pointercancel", () => this._onPointerCancel(), {
            capture: true,
        });
        useListener(document, "keydown", (ev) => this._onKeyDown(ev), {
            capture: true,
        });
        for (const type of ["click", "keyup", "pointerup", "pointercancel"]) {
            useListener(document, type, () => (this.isUserInteracting = false));
        }
        useListener(rpcBus, "RPC:REQUEST", (ev) => {
            this.pendingRpcIds.add(ev.detail.data.id);
            this._update();
        });
        useListener(rpcBus, "RPC:RESPONSE", (ev) => {
            this.pendingRpcIds.delete(ev.detail.data.id);
            if (!this.pendingRpcIds.size) {
                for (const callback of this.rpcsDoneCallbacks.splice(0)) {
                    callback();
                }
            }
            this._update();
        });
        onWillDestroy(() => {
            this.isDestroyed = true;
            this.observer?.disconnect();
        });
        this._updateForAnimation = useThrottleForAnimation(() => this._update());
        this._saveResumeUrl = useDebounced((tutorial) => {
            const url = router.stateToUrl(router.current);
            if (tutorial.resumeUrl !== url) {
                tutorial.resumeUrl = url;
                this.orm.silent.call("web_tuto.tutorial", "save_resume_url", [[tutorial.id], url]);
            }
        }, 500);
    }

    /**
     * Ends the tutorial for the user: finished, skipped or marked as done
     * @param {Tutorial} tutorial
     */
    endTutorial(tutorial) {
        this.tutorials = this.tutorials.filter((running) => running !== tutorial);
        this.orm.silent.call("web_tuto.tutorial", "mark_done", [[tutorial.id]]);
        if (!this.tutorials.length) {
            this.observer.disconnect();
            this._saveResumeUrl.cancel();
            Object.assign(pointerState, { trigger: undefined, content: "" });
            this.pointedStep = null;
            return;
        }
        this._update();
    }

    /**
     * Loads the running tutorials and, if any, their engine and the pointer
     * @private
     */
    async _bootstrap() {
        await whenReady();
        if (window.frameElement || !session.tutorial_enabled || !session.has_running_tutorials) {
            return;
        }
        const definitions = registry.category("web_tuto.tutorials");
        const tutorials = (
            await this.orm.silent.call("web_tuto.tutorial", "get_running_tutorials")
        ).filter(({ name }) => definitions.contains(name));
        if (this.isDestroyed || !tutorials.length) {
            return;
        }
        if (!odoo.loader.modules.get("@web_tuto/tutorial/tutorial")) {
            await loadBundle("web_tuto.tutorial", { css: false });
            if (this.isDestroyed) {
                return;
            }
        }
        const { Tutorial } = odoo.loader.modules.get("@web_tuto/tutorial/tutorial");
        const { TourInteractiveObserver } = odoo.loader.modules.get(
            "@web_tour/tour_interactive/tour_interactive_observer"
        );
        this.domUtils = odoo.loader.modules.get("@web_tuto/tutorial/utils");
        this.tutorials = tutorials.map((data) => new Tutorial(data, definitions.get(data.name)));
        pointerState.tipsShown = Boolean(session.tutorial_tips_shown);
        this.overlay.add(TutorialPointer, {}, { sequence: 1100 });
        this.observer = new TourInteractiveObserver(() => this._updateForAnimation());
        this.observer.start(document);
        this._update();
    }

    /**
     * @param {ParentNode} root
     * @returns {{ step: TutorialStep | null, anchor?: HTMLElement }} the first
     *   displayed step that can be done, and its element; a done one only
     *   while no RPC is pending
     * @private
     */
    _findStepToPoint(root) {
        for (const step of this._getDisplayedSteps(root)) {
            if (step.done && this.pendingRpcIds.size) {
                continue;
            }
            const anchor = step.findAnchor(root);
            if (anchor) {
                return { step, anchor };
            }
        }
        return { step: null };
    }

    /**
     * @returns {DisplayedView | undefined} the view of the current controller,
     *   if it's a window action
     * @private
     */
    _getControllerView() {
        const controller = this.action.currentController;
        return (
            controller?.view && { resModel: controller.props.resModel, type: controller.view.type }
        );
    }

    /**
     * @param {ParentNode} root
     * @returns {TutorialStep[]} the steps of the displayed chapters of the
     *   running tutorials (see `Tutorial.getDisplayedSteps`)
     * @private
     */
    _getDisplayedSteps(root) {
        const view =
            root === document
                ? this._getControllerView()
                : dialogViews.get(root.closest(".o_dialog")?.id)?.();
        return this.tutorials.flatMap((tutorial) => tutorial.getDisplayedSteps(root, view));
    }

    /**
     * @param {{ anchor: HTMLElement, content: string }} invalidField
     * @returns {Partial<TutorialPointerState>}
     * @private
     */
    _getInvalidFieldPointer(invalidField) {
        return {
            ...HIDDEN_POINTER,
            alwaysOpen: true,
            content: invalidField.content,
            invalid: true,
            trigger: invalidField.anchor,
        };
    }

    /**
     * @param {TutorialStep | null} step
     * @param {HTMLElement} [anchor]
     * @returns {Partial<TutorialPointerState>}
     * @private
     */
    _getStepPointer(step, anchor) {
        if (!step) {
            return HIDDEN_POINTER;
        }
        const { steps } = step.tutorial;
        return {
            ...HIDDEN_POINTER,
            alwaysOpen: step.hint,
            content: step.content,
            onNext: this.onNext,
            progress: _t("Step %(current)s/%(total)s", {
                current: steps.indexOf(step) + 1,
                total: steps.length,
            }),
            side: step.tooltipPosition,
            trigger: anchor,
        };
    }

    /**
     * @returns {boolean} whether the user drags an element
     * @private
     */
    _isDragging() {
        return this.tutorials.some((tutorial) => tutorial.isDragging);
    }

    /**
     * Marks the steps as done, a done step being done again; only a finished
     * tutorial is saved as such, not to write its progress twice at once
     * @param {TutorialStep[]} steps
     * @private
     */
    _markDone(steps) {
        const undoneSteps = steps
            .filter((step) => step.done)
            .flatMap((step) => step.resetNextSteps());
        this._saveSteps("mark_steps_undone", undoneSteps);
        const newSteps = steps.filter((step) => !step.done);
        for (const step of newSteps) {
            step.done = true;
            step.tutorial.chapterIndex = Math.max(step.tutorial.chapterIndex, step.chapter.index);
        }
        this._saveSteps(
            "mark_steps_done",
            newSteps.filter((step) => !step.tutorial.isDone)
        );
        for (const tutorial of new Set(steps.map((step) => step.tutorial))) {
            if (tutorial.isDone) {
                this.endTutorial(tutorial);
                if (tutorial.rainbowManMessage) {
                    this.effect.add({
                        message: tutorial.rainbowManMessage,
                        type: "rainbow_man",
                    });
                }
            }
        }
        this._update();
    }

    /**
     * Marks as done the first displayed step of each tutorial done by the
     * user's interaction (e.g. only the first of two steps adding a stage)
     * @param {(step: TutorialStep, root: ParentNode) => boolean} doesStep
     * @private
     */
    _markDoneBy(doesStep) {
        if (!this.tutorials.length) {
            return;
        }
        const root = this.domUtils.getRoot();
        const doneOnTarget = this._getDisplayedSteps(root).filter(
            (step) => (!step.done || step === this.pointedStep) && doesStep(step, root)
        );
        const firstStepByTutorial = new Map();
        for (const step of doneOnTarget) {
            if (!firstStepByTutorial.has(step.tutorial)) {
                firstStepByTutorial.set(step.tutorial, step);
            }
        }
        const steps = [...firstStepByTutorial.values()];
        if (steps.length) {
            this._markDone(steps);
        }
    }

    /**
     * Marks as done the field steps the user focused or pressed
     * @param {EventTarget} target
     * @private
     */
    _markFieldDoneBy(target) {
        if (this.isUserInteracting && target instanceof Element) {
            this._markDoneBy((step, root) => step.type === "field" && step.isDoneBy(root, target));
        }
    }

    /**
     * Does the action steps clicked by the user, outside the pointer
     * @param {MouseEvent} ev
     * @private
     */
    _onClick(ev) {
        if (ev.target instanceof Element && !ev.target.closest(".o_tutorial_pointer_content")) {
            this._markDoneBy(
                (step, root) => step.type === "action" && step.isDoneBy(root, ev.target)
            );
        }
    }

    /**
     * Does the field steps typed in
     * @param {KeyboardEvent} ev
     * @private
     */
    _onKeyDown(ev) {
        this.isUserInteracting = true;
        browser.setTimeout(() => (this.isUserInteracting = false));
        this._markFieldDoneBy(ev.target);
    }

    /**
     * Stops pointing the drop steps of the element whose drag was cancelled
     * @private
     */
    _onPointerCancel() {
        this.dragStart = null;
        if (this._isDragging()) {
            this._setDragging(false);
            this._update();
        }
    }

    /**
     * Does the field steps pressed by the user, who may start to drag
     * @param {PointerEvent} ev
     * @private
     */
    _onPointerDown(ev) {
        this.isUserInteracting = true;
        this.dragStart =
            ev.target instanceof Element
                ? { source: ev.target, x: ev.clientX, y: ev.clientY }
                : null;
        this._markFieldDoneBy(ev.target);
    }

    /**
     * Does the drag steps of the element the user started to drag (moving
     * the pointer pressed on it), pointing their drop steps meanwhile
     * @param {PointerEvent} ev
     * @private
     */
    _onPointerMove(ev) {
        const { dragStart } = this;
        if (
            !dragStart ||
            this._isDragging() ||
            Math.hypot(ev.clientX - dragStart.x, ev.clientY - dragStart.y) < DRAG_DISTANCE
        ) {
            return;
        }
        this._setDragging(true);
        this._markDoneBy((step, root) => step.isDoneByDrag(root, dragStart.source));
        this._update();
    }

    /**
     * Does the drop steps of the element dropped by the user
     * @param {PointerEvent} ev
     * @private
     */
    _onPointerUp(ev) {
        const { dragStart } = this;
        this.dragStart = null;
        if (dragStart && this._isDragging()) {
            this._markDoneBy((step, root) => step.isDoneByDrop(root, dragStart.source, ev));
            this._setDragging(false);
            this._update();
        }
    }

    /**
     * @param {boolean} isDragging whether the user drags an element
     * @private
     */
    _setDragging(isDragging) {
        for (const tutorial of this.tutorials) {
            tutorial.isDragging = isDragging;
        }
    }

    /**
     * Saves the steps as done or undone by the user, by tutorial
     * @param {"mark_steps_done"|"mark_steps_undone"} method
     * @param {TutorialStep[]} steps
     * @private
     */
    _saveSteps(method, steps) {
        for (const tutorial of new Set(steps.map((step) => step.tutorial))) {
            const keys = steps.filter((step) => step.tutorial === tutorial).map((step) => step.key);
            this.orm.silent.call("web_tuto.tutorial", method, [[tutorial.id], keys]);
        }
    }

    /**
     * Points the first step to do among the displayed ones, or the first
     * invalid field of their view
     * @private
     */
    _update() {
        if (!this.tutorials.length) {
            return;
        }
        const root = this.domUtils.getRoot();
        const { step, anchor } = this._findStepToPoint(root);
        this.pointedStep = step;
        if (step && !step.done) {
            this._saveResumeUrl(step.tutorial);
        } else {
            this._saveResumeUrl.cancel();
        }
        const invalidField = step && this.domUtils.findInvalidField(root);
        const pointed = invalidField
            ? this._getInvalidFieldPointer(invalidField)
            : this._getStepPointer(step, anchor);
        if (pointed.trigger && this.domUtils.isCovered(pointed.trigger)) {
            pointed.trigger = undefined;
        }
        Object.assign(pointerState, { ...pointed, onSkip: this.onSkip });
    }

    /**
     * @returns {Promise<void>} resolved once no RPC is pending anymore, and
     *   the web client rendered their results (e.g. a kanban view its new
     *   column, its response only being processed after its RPC ended)
     * @private
     */
    async _waitForRpcs() {
        while (this.pendingRpcIds.size) {
            await new Promise((resolve) => this.rpcsDoneCallbacks.push(resolve));
            await new Promise((resolve) => browser.requestAnimationFrame(resolve));
        }
    }
}

services.add(TutorialPlugin);
