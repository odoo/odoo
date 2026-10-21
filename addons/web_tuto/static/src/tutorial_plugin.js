import {
    onWillDestroy,
    onWillStart,
    Plugin,
    useListener,
    usePlugin,
    whenReady,
} from "@odoo/owl";
import { location } from "@web/core/browser/browser";
import { EffectPlugin } from "@web/core/effects/effect_plugin";
import { rpcBus } from "@web/core/network/rpc";
import { ORM } from "@web/core/orm_plugin";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { session } from "@web/session";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";
import { dialogViewProps } from "@web_tuto/dialog_views";
import { TutorialAction } from "@web_tuto/tutorial_action";
import { TutorialObserver } from "@web_tuto/tutorial_observer";
import { TutorialPointer, pointerState } from "@web_tuto/tutorial_pointer/tutorial_pointer";
import { TutorialItem } from "@web_tuto/widgets/tutorial_item";

/**
 * Guides the user through the running tutorials, view by view: in each
 * displayed view of a tutorial, the pointer shows the first action not done
 * yet. An action is done once its field is focused or its button clicked, or
 * with the "Next" button of the pointer. A tutorial is finished once the
 * actions of its last view are done.
 *
 * The views of a tutorial are its chapters:
 * - in the current chapter (the last one with a done action) or a next one,
 *   when none of its remaining actions can be done (e.g. the record failed to
 *   be saved, or its quick create was discarded), the pointer goes back to its
 *   last done action that can be done again;
 * - in a previous chapter, the pointer goes back to its last done action.
 * Doing an action again resets the actions done after it, from its chapter.
 * The pointer doesn't go back while an RPC is pending, as the next view may be
 * loading.
 */
export class TutorialPlugin extends Plugin {
    orm = usePlugin(ORM);
    effect = usePlugin(EffectPlugin);
    overlay = usePlugin(OverlayPlugin);
    action = usePlugin(ActionPlugin);

    tutorialsEnabled = session?.tutorial_enabled;
    tutorials = [];
    /** @type {TutorialAction | null} */
    currentAction = null;
    /** Whether the user is pressing a pointer or a key, to ignore the autofocus */
    isUserInteracting = false;
    /** The ids of the pending RPCs, during which the pointer doesn't go back */
    pendingRpcIds = new Set();
    onNext = () => this.currentAction && this.doAction(this.currentAction);
    onSkip = () => this.currentAction && this.consume(this.currentAction.tutorial);

    setup() {
        onWillStart(() => this.bootstrap());
        useListener(document, "click", (ev) => this.onClick(ev), { capture: true });
        useListener(document, "focusin", (ev) => this.onFocusIn(ev), { capture: true });
        for (const type of ["pointerdown", "keydown"]) {
            useListener(document, type, (ev) => this.onUserInteraction(ev), { capture: true });
        }
        for (const type of ["click", "keyup", "pointerup", "pointercancel"]) {
            useListener(document, type, () => (this.isUserInteracting = false));
        }
        useListener(rpcBus, "RPC:REQUEST", (ev) => {
            this.pendingRpcIds.add(ev.detail.data.id);
            this.update();
        });
        useListener(rpcBus, "RPC:RESPONSE", (ev) => {
            this.pendingRpcIds.delete(ev.detail.data.id);
            this.update();
        });
        onWillDestroy(() => this.observer?.disconnect());
    }

    async bootstrap() {
        await whenReady();
        this.addTutorialItemInDebugMenu();
        if (window.frameElement || !this.tutorialsEnabled || !session.has_running_tutorials) {
            return;
        }
        const tutorials = await this.orm.silent.call("web_tuto.tutorial", "get_running_tutorials");
        for (const tutorial of tutorials) {
            for (const view of tutorial.views) {
                view.actions = view.actions.map((data) => new TutorialAction(data, view, tutorial));
            }
            const lastStartedIndex = tutorial.views.findLastIndex((view) =>
                view.actions.some((action) => action.done)
            );
            tutorial.chapter = Math.max(lastStartedIndex, 0);
        }
        this.tutorials = tutorials;
        if (!tutorials.length) {
            return;
        }
        this.overlay.add(TutorialPointer, { pointerState }, { sequence: 1100 });
        this.observer = new TutorialObserver(() => this.update());
        this.observer.observe(document);
        this.update();
    }

    addTutorialItemInDebugMenu() {
        const debugMenuRegistry = registry.category("debug").category("default");
        debugMenuRegistry.add("tutorialItem", () => ({
            type: "component",
            Component: TutorialItem,
            props: {
                tutorialsEnabled: this.tutorialsEnabled || false,
                toggleItem: async () => {
                    this.tutorialsEnabled = await this.orm.call(
                        "res.users",
                        "switch_tutorial_enabled",
                        [!this.tutorialsEnabled]
                    );
                    location.reload();
                },
            },
            sequence: 510,
            section: "testing",
        }));
    }

    /**
     * @returns {ParentNode} the dialog on top of the others if any, the
     *   document otherwise
     */
    getRoot() {
        const modals = [...document.querySelectorAll(".modal")].filter(
            (el) => el.getClientRects().length
        );
        return modals.at(-1) || document;
    }

    /**
     * @param {ParentNode} root
     * @returns {TutorialAction[]} the actions of the displayed chapters of the
     *   running tutorials: in the current chapter or a next one, the ones not
     *   done yet, then the done ones from the last, to go back to; in a
     *   previous chapter, the done ones from the last first
     */
    getDisplayedActions(root) {
        const props =
            root === document
                ? this.action.currentController?.props
                : dialogViewProps.get(root.closest(".o_dialog")?.id)?.();
        const isDisplayed = (view) =>
            root.querySelector(`.o_${view.type}_view`) &&
            props?.resModel === view.model &&
            props.type === view.type;
        return this.tutorials.flatMap((tutorial) => {
            const displayedViews = tutorial.views.filter(isDisplayed);
            const view = displayedViews.find(
                (view) => tutorial.views.indexOf(view) >= tutorial.chapter
            );
            const previousView = view ? null : displayedViews.at(-1);
            if (!view && !previousView) {
                return [];
            }
            const { actions } = view || previousView;
            const doneActions = actions.filter((action) => action.done).reverse();
            const actionsToDo = actions.filter((action) => !action.done);
            return view ? [...actionsToDo, ...doneActions] : [...doneActions, ...actionsToDo];
        });
    }

    update() {
        if (!this.tutorials.length) {
            return;
        }
        const root = this.getRoot();
        const current = this.getDisplayedActions(root).find(
            (action) => (!action.done || !this.pendingRpcIds.size) && action.findAnchor(root)
        );
        this.currentAction = current || null;
        Object.assign(pointerState, {
            trigger: current?.findAnchor(root),
            content: current?.content || "",
            position: current?.tooltip_position,
            onNext: this.onNext,
            onSkip: this.onSkip,
        });
    }

    /**
     * @param {MouseEvent} ev
     */
    onClick(ev) {
        if (!(ev.target instanceof Element) || ev.target.closest(".o_tutorial_pointer_content")) {
            return;
        }
        this.markDoneOn(ev.target, (action) => action.kind !== "field");
    }

    /**
     * The user may also use a field that already has the focus (autofocus)
     * @param {PointerEvent | KeyboardEvent} ev
     */
    onUserInteraction(ev) {
        this.isUserInteracting = true;
        this.onFocusIn(ev);
    }

    /**
     * @param {FocusEvent} ev
     */
    onFocusIn(ev) {
        if (this.isUserInteracting && ev.target instanceof Element) {
            this.markDoneOn(ev.target, (action) => action.kind === "field");
        }
    }

    /**
     * @param {Element} target
     * @param {(action: TutorialAction) => boolean} filter
     */
    markDoneOn(target, filter) {
        if (!this.tutorials.length) {
            return;
        }
        const root = this.getRoot();
        const actions = this.getDisplayedActions(root).filter(
            (action) =>
                (!action.done || action === this.currentAction) &&
                filter(action) &&
                action.isDoneOn(target, root)
        );
        if (actions.length) {
            this.markDone(actions);
        }
    }

    /**
     * Does the action for the user ("Next" button): clicks its button or
     * focuses its field, a hint being only shown
     * @param {TutorialAction} action
     */
    doAction(action) {
        const anchor = action.findAnchor(this.getRoot());
        if (anchor && !action.hint) {
            if (action.kind === "field") {
                anchor.focus();
            } else {
                anchor.click();
            }
        }
        this.markDone([action]);
    }

    /**
     * Marks the actions as done, an action already done being done again
     * @param {TutorialAction[]} actions
     */
    markDone(actions) {
        for (const action of actions.filter((action) => action.done)) {
            this.redo(action);
        }
        const newActions = actions.filter((action) => !action.done);
        for (const action of newActions) {
            action.done = true;
            const { tutorial } = action;
            tutorial.chapter = Math.max(tutorial.chapter, tutorial.views.indexOf(action.view));
        }
        if (newActions.length) {
            this.orm.silent.call("web_tuto.step", "mark_done", [
                newActions.map((action) => action.id),
            ]);
        }
        for (const tutorial of new Set(actions.map((action) => action.tutorial))) {
            if (tutorial.views.at(-1).actions.every((action) => action.done)) {
                this.consume(tutorial);
                if (tutorial.rainbowManMessage) {
                    this.effect.add({ type: "rainbow_man", message: tutorial.rainbowManMessage });
                }
            }
        }
        this.update();
    }

    /**
     * Resets the done actions after an action done again, of its view and of
     * the next ones: the tutorial goes on from its chapter
     * @param {TutorialAction} action
     */
    redo(action) {
        const { tutorial, view } = action;
        const viewIndex = tutorial.views.indexOf(view);
        const nextActions = [
            ...view.actions.slice(view.actions.indexOf(action) + 1),
            ...tutorial.views.slice(viewIndex + 1).flatMap((nextView) => nextView.actions),
        ].filter((nextAction) => nextAction.done);
        for (const nextAction of nextActions) {
            nextAction.done = false;
        }
        tutorial.chapter = viewIndex;
        if (nextActions.length) {
            this.orm.silent.call("web_tuto.step", "mark_undone", [
                nextActions.map((nextAction) => nextAction.id),
            ]);
        }
    }

    /**
     * @param {Object} tutorial
     */
    consume(tutorial) {
        this.tutorials = this.tutorials.filter((t) => t !== tutorial);
        this.orm.silent.call("web_tuto.tutorial", "consume", [[tutorial.id]]);
        if (!this.tutorials.length) {
            this.observer.disconnect();
            Object.assign(pointerState, { trigger: undefined, content: "" });
            this.currentAction = null;
            return;
        }
        this.update();
    }
}

services.add(TutorialPlugin);
