import { onWillDestroy, onWillStart, Plugin, useListener, usePlugin, whenReady } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { router } from "@web/core/browser/router";
import { EffectPlugin } from "@web/core/effects/effect_plugin";
import { _t } from "@web/core/l10n/translation";
import { rpcBus } from "@web/core/network/rpc";
import { ORM } from "@web/core/orm_plugin";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { services } from "@web/core/services";
import { useDebounced } from "@web/core/utils/timing";
import { session } from "@web/session";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";
import { dialogViewProps } from "@web_tuto/dialog_views";
import { TutorialPointer } from "@web_tuto/pointer/pointer";
import { pointerState } from "@web_tuto/pointer/pointer_state";

/**
 * Guides the user through the running tutorials, chapter by chapter: a
 * chapter is a view of a tutorial with its steps, shown in that view (or, for
 * a view of several records such as a list, in any such view of its model).
 * For instance, the tutorial of CRM goes through the kanban view of the leads
 * (New, then the customer, the expected revenue and the priority of the new
 * lead, then Edit), then through the form view of a lead (its tags, its
 * description...).
 *
 * In the displayed chapter, the pointer shows the first step not done yet,
 * whatever the order in which the user does them. A step is done once its
 * field is focused or its button clicked by the user, or with the "Next"
 * button of the pointer. The current chapter of a tutorial is the last one
 * with a done step. A tutorial is finished once the steps of its last chapter
 * are done.
 *
 * - In the current chapter (the last one with a done step) or a next one, when
 *   none of its remaining steps can be done (e.g. the record failed to be
 *   saved), the pointer goes back to its last done step that can be done
 *   again; in a previous chapter, to its last done step. Doing a step again
 *   resets the steps done after it. The pointer doesn't go back while an RPC
 *   is pending, as the next view may be loading.
 * - While a field of the view is invalid (e.g. a required field left empty),
 *   the pointer shows it instead, the user having to fill it in to go on.
 * - The pointer hides while what it points at is covered (e.g. by a dropdown).
 * - The URL of the view where the user has a step to do is saved, to resume
 *   the tutorial there.
 */
export class TutorialPlugin extends Plugin {
    orm = usePlugin(ORM);
    effect = usePlugin(EffectPlugin);
    overlay = usePlugin(OverlayPlugin);
    action = usePlugin(ActionPlugin);

    tutorials = [];
    /**
     * The helpers of the engine (`@web_tuto/tutorial/utils`), in the bundle
     * only loaded once some tutorials run
     */
    engine = null;
    /** @type {TutorialStep | null} */
    currentStep = null;
    /** Whether the user is pressing a pointer or a key, to ignore the autofocus */
    isUserInteracting = false;
    /** The ids of the pending RPCs, during which the pointer doesn't go back */
    pendingRpcIds = new Set();
    onNext = () => {
        const step = this.currentStep;
        if (step) {
            this._markDone([step]);
            step.perform(this.engine.getRoot());
        }
    };
    onSkip = () => this.currentStep && this.endTutorial(this.currentStep.tutorial);

    /**
     * Starts the running tutorials once the web client is ready, and listens
     * to the user's interactions and to the RPCs
     */
    setup() {
        onWillStart(() => this._bootstrap());
        useListener(
            document,
            "click",
            (ev) => {
                if (
                    ev.target instanceof Element &&
                    !ev.target.closest(".o_tutorial_pointer_content")
                ) {
                    this._markDoneOn(ev.target, (step) => step.type !== "field");
                }
            },
            { capture: true }
        );
        useListener(document, "focusin", (ev) => this._onFocusIn(ev), { capture: true });
        for (const type of ["pointerdown", "keydown"]) {
            useListener(
                document,
                type,
                (ev) => {
                    this.isUserInteracting = true;
                    this._onFocusIn(ev);
                },
                { capture: true }
            );
        }
        for (const type of ["click", "keyup", "pointerup", "pointercancel"]) {
            useListener(document, type, () => (this.isUserInteracting = false));
        }
        useListener(rpcBus, "RPC:REQUEST", (ev) => {
            this.pendingRpcIds.add(ev.detail.data.id);
            this._update();
        });
        useListener(rpcBus, "RPC:RESPONSE", (ev) => {
            this.pendingRpcIds.delete(ev.detail.data.id);
            this._update();
        });
        onWillDestroy(() => this.observer?.disconnect());
        this._saveResumeUrl = useDebounced((tutorial) => {
            const url = router.stateToUrl(router.current);
            if (tutorial.resumeUrl !== url) {
                tutorial.resumeUrl = url;
                this.orm.silent.call("web_tuto.tutorial", "save_resume_url", [[tutorial.id], url]);
            }
        }, 500);
    }

    /**
     * Loads the running tutorials of the user, each one starting from its last
     * view with a done step, and shows the pointer if there are any, their
     * engine being only loaded then
     * @private
     */
    async _bootstrap() {
        await whenReady();
        if (window.frameElement || !session.tutorial_enabled || !session.has_running_tutorials) {
            return;
        }
        const tutorials = await this.orm.silent.call("web_tuto.tutorial", "get_running_tutorials");
        if (!tutorials.length) {
            return;
        }
        if (!odoo.loader.modules.get("@web_tuto/tutorial/tutorial")) {
            await loadBundle("web_tuto.tutorial", { css: false });
        }
        const { Tutorial } = odoo.loader.modules.get("@web_tuto/tutorial/tutorial");
        const { TourInteractiveObserver } = odoo.loader.modules.get(
            "@web_tour/tour_interactive/tour_interactive_observer"
        );
        this.engine = odoo.loader.modules.get("@web_tuto/tutorial/utils");
        this.tutorials = tutorials.map((data) => new Tutorial(data));
        pointerState.tipsShown = Boolean(session.tutorial_tips_shown);
        this.overlay.add(TutorialPointer, {}, { sequence: 1100 });
        this.observer = new TourInteractiveObserver(() => this._update());
        this.observer.start(document);
        this._update();
    }

    /**
     * Ends the tutorial for the user (finished, skipped or marked as done),
     * hiding the pointer once no tutorial runs anymore
     * @param {Tutorial} tutorial
     */
    endTutorial(tutorial) {
        this.tutorials = this.tutorials.filter((t) => t !== tutorial);
        this.orm.silent.call("web_tuto.tutorial", "mark_done", [[tutorial.id]]);
        if (!this.tutorials.length) {
            this.observer.disconnect();
            Object.assign(pointerState, { trigger: undefined, content: "" });
            this.currentStep = null;
            return;
        }
        this._update();
    }

    /**
     * @param {ParentNode} root
     * @returns {TutorialStep[]} the steps of the displayed chapters of the
     *   running tutorials (see `Tutorial.getDisplayedSteps`)
     * @private
     */
    _getDisplayedSteps(root) {
        const props =
            root === document
                ? this.action.currentController?.props
                : dialogViewProps.get(root.closest(".o_dialog")?.id)?.();
        return this.tutorials.flatMap((tutorial) => tutorial.getDisplayedSteps(root, props));
    }

    /**
     * Marks the steps as done, a step already done being done again
     * @param {TutorialStep[]} steps
     * @private
     */
    _markDone(steps) {
        const undoneSteps = steps.filter((step) => step.done).flatMap((step) => step.redo());
        if (undoneSteps.length) {
            this.orm.silent.call("web_tuto.step", "mark_undone", [
                undoneSteps.map((step) => step.id),
            ]);
        }
        const newSteps = steps.filter((step) => !step.done);
        for (const step of newSteps) {
            step.done = true;
            step.tutorial.chapterIndex = Math.max(step.tutorial.chapterIndex, step.chapter.index);
        }
        if (newSteps.length) {
            this.orm.silent.call("web_tuto.step", "mark_done", [newSteps.map((step) => step.id)]);
        }
        for (const tutorial of new Set(steps.map((step) => step.tutorial))) {
            if (tutorial.isDone) {
                this.endTutorial(tutorial);
                if (tutorial.rainbowManMessage) {
                    this.effect.add({ type: "rainbow_man", message: tutorial.rainbowManMessage });
                }
            }
        }
        this._update();
    }

    /**
     * Marks as done the first displayed step of each tutorial done on the
     * target (e.g. only the first of two steps adding a stage), the current
     * step being done again if it was already done
     * @param {Element} target
     * @param {(step: TutorialStep) => boolean} filter
     * @private
     */
    _markDoneOn(target, filter) {
        if (!this.tutorials.length) {
            return;
        }
        const root = this.engine.getRoot();
        const doneOnTarget = this._getDisplayedSteps(root).filter(
            (step) =>
                (!step.done || step === this.currentStep) &&
                filter(step) &&
                step.isDoneOn(root, target)
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
     * Marks as done the field steps focused by the user, the focus not
     * coming from them (e.g. autofocus) being ignored
     * @param {FocusEvent} ev
     * @private
     */
    _onFocusIn(ev) {
        if (this.isUserInteracting && ev.target instanceof Element) {
            this._markDoneOn(ev.target, (step) => step.type === "field");
        }
    }

    /**
     * Points the first step to do among the displayed ones (not going back to
     * a done step while an RPC is pending), or the first invalid field of
     * their view
     * @private
     */
    _update() {
        if (!this.tutorials.length) {
            return;
        }
        const root = this.engine.getRoot();
        const current = this._getDisplayedSteps(root).find(
            (step) => (!step.done || !this.pendingRpcIds.size) && step.findAnchor(root)
        );
        this.currentStep = current || null;
        if (current && !current.done) {
            this._saveResumeUrl(current.tutorial);
        } else {
            this._saveResumeUrl.cancel();
        }
        const invalidField = current && this.engine.findInvalidField(root);
        let pointed;
        if (invalidField) {
            pointed = {
                trigger: invalidField.anchor,
                content: invalidField.content,
                progress: "",
                position: "bottom",
                hint: true,
                onNext: undefined,
            };
        } else {
            const tutorialSteps = current?.tutorial.steps;
            pointed = {
                trigger: current?.findAnchor(root),
                content: current?.content || "",
                progress: current
                    ? _t("Step %(current)s/%(total)s", {
                          current: tutorialSteps.indexOf(current) + 1,
                          total: tutorialSteps.length,
                      })
                    : "",
                position: current?.tooltipPosition,
                hint: Boolean(current?.hint),
                onNext: this.onNext,
            };
        }
        if (pointed.trigger && this.engine.isCovered(pointed.trigger)) {
            pointed.trigger = undefined;
        }
        Object.assign(pointerState, { ...pointed, onSkip: this.onSkip });
    }
}

services.add(TutorialPlugin);
