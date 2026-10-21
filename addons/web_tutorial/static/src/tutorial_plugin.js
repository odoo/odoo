import {
    onWillDestroy,
    onWillStart,
    Plugin,
    useListener,
    useOnChange,
    usePlugin,
    whenReady,
} from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { EffectPlugin } from "@web/core/effects/effect_plugin";
import { ORM } from "@web/core/orm_plugin";
import { rpcBus } from "@web/core/network/rpc";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { services } from "@web/core/services";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { session } from "@web/session";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";
import { dialogViews } from "@web_tutorial/displayed_views";
import {
    getInvalidFieldPointer,
    getStepPointer,
    HIDDEN_POINTER,
    pointerState,
} from "@web_tutorial/pointer/pointer_state";
import { TutorialPointer } from "@web_tutorial/pointer/tutorial_pointer";
import { useRpcTracker } from "@web_tutorial/rpc_tracker";

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
 */
export class TutorialPlugin extends Plugin {
    #action = usePlugin(ActionPlugin);
    /**
     * The DOM helpers of the tutorials (`@web_tutorial/tutorial/utils`), in the
     * bundle only loaded once some tutorials run
     */
    #domUtils = null;
    #effect = usePlugin(EffectPlugin);
    /** Whether the plugin is destroyed, e.g. before its bootstrap ended */
    #isDestroyed = false;
    /** Whether Next is doing a step, not to do it twice */
    #isPerforming = false;
    /**
     * Whether the user is pressing a pointer or a key, an autofocus not doing
     * a field step
     */
    #isUserInteracting = false;
    /**
     * Updates the pointer on any change of the page
     * @type {MutationObserver | null}
     */
    #observer = null;
    /**
     * Does the pointed step once no RPC is pending (e.g. a kanban view being
     * reloaded), unless the user left its view or did it meanwhile. A button
     * is marked done by its click, as when the user does it. Next is ignored
     * while doing a step, and does nothing if the dropdown of the step doesn't
     * open.
     */
    onNext = async () => {
        const step = this.#pointedStep;
        if (!step || this.#isPerforming) {
            return;
        }
        this.#isPerforming = true;
        try {
            await this.#rpcs.waitForIdle();
            const root = this.#domUtils.getRoot();
            const isViewLeft = !this.#getDisplayedSteps(root).includes(step);
            const isDoneByUserMeanwhile = step.done && step !== this.#pointedStep;
            if (isViewLeft || isDoneByUserMeanwhile) {
                return;
            }
            if (step.type === "field" || step.hint) {
                this.#markStepsDone([step]);
            }
            await step.perform(root);
        } catch (error) {
            if (error.name !== "HootTimingError") {
                throw error;
            }
        } finally {
            this.#isPerforming = false;
        }
    };
    onSkip = () => this.#pointedStep && this.endTutorial(this.#pointedStep.tutorial);
    #orm = usePlugin(ORM);
    #overlay = usePlugin(OverlayPlugin);
    /**
     * The step the pointer shows, which may be a done step to do again
     * @type {TutorialStep | null}
     */
    #pointedStep = null;
    /**
     * The pending RPCs (but the ones saving the progress), during which the
     * pointer doesn't go back
     */
    #rpcs = null;
    tutorials = [];
    #updateForAnimation = null;

    /**
     * Starts the running tutorials without delaying the web client, only
     * listening to the user once some run
     */
    setup() {
        if (window.frameElement || !session.running_tutorials?.length) {
            return;
        }
        onWillStart(() => {
            this.#bootstrap();
        });
        const handlers = {
            click: (ev) => this.#onClick(ev),
            focusin: (ev) => this.#markFieldDoneBy(ev.target),
            keydown: (ev) => this.#onKeyDown(ev),
            pointerdown: (ev) => this.#onPointerDown(ev),
        };
        for (const [type, handler] of Object.entries(handlers)) {
            useListener(window, type, handler, { capture: true });
        }
        for (const type of ["click", "keyup", "pointerup", "pointercancel"]) {
            useListener(window, type, () => (this.#isUserInteracting = false));
        }
        this.#rpcs = useRpcTracker("web_tutorial.tutorial");
        useListener(rpcBus, "RPC:RESPONSE", ({ detail }) => {
            const { method, model } = detail.data.params || {};
            if (model === "web_tutorial.tutorial" && method?.startsWith("web_save") && !detail.error) {
                this.#reloadOptions();
            }
        });
        useOnChange(
            () => [this.#rpcs.isPending()],
            () => this.#update(),
            { initialRun: false }
        );
        onWillDestroy(() => {
            this.#isDestroyed = true;
            this.#observer?.disconnect();
        });
        this.#updateForAnimation = useThrottleForAnimation(() => this.#update());
    }

    /**
     * Ends the tutorial for the user: finished or skipped
     * @param {Tutorial} tutorial
     */
    endTutorial(tutorial) {
        this.tutorials = this.tutorials.filter((running) => running !== tutorial);
        tutorial.end();
        if (!this.tutorials.length) {
            this.#observer?.disconnect();
            Object.assign(pointerState, HIDDEN_POINTER);
            this.#pointedStep = null;
            return;
        }
        this.#update();
    }

    /**
     * Reads again the options of the running tutorials (e.g. one switched to
     * always show its tooltips), saved meanwhile in their list or form
     */
    async #reloadOptions() {
        if (!this.tutorials.length) {
            return;
        }
        const records = await this.#orm.silent.read(
            "web_tutorial.tutorial",
            this.tutorials.map(({ id }) => id),
            ["always_show_tooltip"]
        );
        for (const { id, always_show_tooltip } of records) {
            const tutorial = this.tutorials.find((running) => running.id === id);
            if (tutorial) {
                tutorial.alwaysShowTooltip = always_show_tooltip;
            }
        }
        this.#update();
    }

    /**
     * Loads the engine of the running tutorials, given by the session with
     * their chapters, and the pointer
     */
    async #bootstrap() {
        await whenReady();
        if (this.#isDestroyed) {
            return;
        }
        if (!odoo.loader.modules.get("@web_tutorial/tutorial/tutorial")) {
            await loadBundle("web_tutorial.tutorial", { css: false });
            if (this.#isDestroyed) {
                return;
            }
        }
        const { Tutorial } = odoo.loader.modules.get("@web_tutorial/tutorial/tutorial");
        this.#domUtils = odoo.loader.modules.get("@web_tutorial/tutorial/utils");
        this.tutorials = session.running_tutorials.map((data) => new Tutorial(data, this.#orm));
        this.#overlay.add(TutorialPointer, {}, { sequence: 1100 });
        this.#observer = new MutationObserver(() => this.#updateForAnimation());
        this.#observer.observe(document, {
            attributes: true,
            characterData: true,
            childList: true,
            subtree: true,
        });
        this.#update();
    }

    /**
     * @param {ParentNode} root
     * @returns {{ step: TutorialStep | null, anchor?: HTMLElement }}
     *   the first displayed step that can be done, and its element; a done
     *   one only while no RPC is pending
     */
    #findStepToPoint(root) {
        for (const step of this.#getDisplayedSteps(root)) {
            if (step.done && this.#rpcs.isPending()) {
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
     */
    #getControllerView() {
        const controller = this.#action.currentController;
        if (controller?.view) {
            const { context, resModel } = controller.props;
            return { context, resModel, type: controller.view.type };
        }
    }

    /**
     * @param {ParentNode} root
     * @returns {TutorialStep[]} the steps of the
     *   displayed chapters of the running tutorials (see
     *   `Tutorial.getDisplayedSteps`)
     */
    #getDisplayedSteps(root) {
        const view =
            root === document
                ? this.#getControllerView()
                : dialogViews.get(root.closest(".o_dialog")?.id)?.();
        return this.tutorials.flatMap((tutorial) => tutorial.getDisplayedSteps(root, view));
    }

    /**
     * Marks the steps as done, at most one by tutorial, ending the tutorials
     * they finish
     * @param {TutorialStep[]} steps
     */
    #markStepsDone(steps) {
        for (const step of steps) {
            const { tutorial } = step;
            tutorial.markStepDone(step);
            if (tutorial.isDone) {
                this.endTutorial(tutorial);
                if (tutorial.rainbowManMessage) {
                    this.#effect.add({
                        message: tutorial.rainbowManMessage,
                        type: "rainbow_man",
                    });
                }
            }
        }
        this.#update();
    }

    /**
     * Marks as done the first displayed step of each tutorial done by the
     * user's interaction (e.g. only the first of two steps of the same field)
     * @param {(step: TutorialStep, root: ParentNode) => boolean} doesStep
     */
    #markDoneBy(doesStep) {
        if (!this.tutorials.length) {
            return;
        }
        const root = this.#domUtils.getRoot();
        const tutorials = new Set();
        const steps = this.#getDisplayedSteps(root).filter((step) => {
            const isDone =
                (!step.done || step === this.#pointedStep) &&
                !tutorials.has(step.tutorial) &&
                doesStep(step, root);
            if (isDone) {
                tutorials.add(step.tutorial);
            }
            return isDone;
        });
        if (steps.length) {
            this.#markStepsDone(steps);
        }
    }

    /**
     * Marks as done the field steps the user focused or pressed
     * @param {EventTarget} target
     */
    #markFieldDoneBy(target) {
        if (this.#isUserInteracting && target instanceof Element) {
            this.#markDoneBy((step, root) => step.type === "field" && step.isDoneBy(root, target));
        }
    }

    /**
     * Does the button steps clicked by the user, outside the pointer
     * @param {MouseEvent} ev
     */
    #onClick(ev) {
        if (ev.target instanceof Element && !ev.target.closest(".o_tutorial_pointer_content")) {
            this.#markDoneBy(
                (step, root) => step.type !== "field" && step.isDoneBy(root, ev.target)
            );
        }
    }

    /**
     * Does the field steps typed in
     * @param {KeyboardEvent} ev
     */
    #onKeyDown(ev) {
        this.#isUserInteracting = true;
        setTimeout(() => (this.#isUserInteracting = false));
        this.#markFieldDoneBy(ev.target);
    }

    /**
     * Does the field steps pressed by the user; pressing the pointer itself
     * doesn't reach the page (e.g. not to close an open dropdown)
     * @param {PointerEvent} ev
     */
    #onPointerDown(ev) {
        if (ev.target instanceof Element && ev.target.closest(".o_tutorial_pointer")) {
            ev.stopImmediatePropagation();
            return;
        }
        this.#isUserInteracting = true;
        this.#markFieldDoneBy(ev.target);
    }

    /**
     * @returns {boolean} whether the view of the current controller or of a
     *   dialog is one of a chapter of the running tutorials, without looking
     *   at the DOM
     */
    #isChapterDisplayed() {
        const views = [
            this.#getControllerView(),
            ...[...dialogViews.values()].map((getView) => getView()),
        ].filter(Boolean);
        return this.tutorials.some((tutorial) =>
            tutorial.chapters.some((chapter) => views.some((view) => chapter.isOfView(view)))
        );
    }

    /**
     * Points the first step to do among the displayed ones, or the first
     * invalid field of their view; only looks at the DOM while a view of a
     * chapter is displayed
     */
    #update() {
        if (!this.tutorials.length) {
            return;
        }
        const root = this.#isChapterDisplayed() && this.#domUtils.getRoot();
        const { step, anchor } = root ? this.#findStepToPoint(root) : { step: null };
        this.#pointedStep = step;
        const invalidField = step && this.#domUtils.findInvalidField(root);
        const pointed = invalidField
            ? getInvalidFieldPointer(invalidField)
            : getStepPointer(step, anchor, this.onNext);
        if (pointed.trigger && this.#domUtils.isCovered(pointed.trigger)) {
            pointed.trigger = undefined;
        }
        if (pointed.trigger) {
            const { top, left, width, height } = pointed.trigger.getBoundingClientRect();
            pointed.triggerRect = `${top},${left},${width},${height}`;
        }
        Object.assign(pointerState, { ...pointed, onSkip: this.onSkip });
    }
}

services.add(TutorialPlugin);
