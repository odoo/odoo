import {
    onWillDestroy,
    markup,
    Plugin,
    useListener,
    useOnChange,
    usePlugin,
    whenReady,
} from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { router } from "@web/core/browser/router";
import { EffectPlugin } from "@web/core/effects/effect_plugin";
import { htmlReplaceAll } from "@web/core/utils/html";
import { ORM } from "@web/core/orm_plugin";
import { rpcBus } from "@web/core/network/rpc";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";
import { LazySessionPlugin } from "@web/webclient/lazy_session_plugin";
import { MenuPlugin } from "@web/webclient/menus/menu_plugin";
import { dialogViews } from "@web_tutorial/displayed_views";
import {
    getInvalidFieldPointer,
    getStepPointer,
    HIDDEN_POINTER,
    pointerState,
} from "@web_tutorial/pointer/pointer_state";
import { TutorialPointer } from "@web_tutorial/pointer/tutorial_pointer";
import { useRpcTracker } from "@web_tutorial/rpc_tracker";

const OBSERVED_CHANGES = { attributes: true, characterData: true, childList: true, subtree: true };

/**
 * @param {Object[]} tutorials the running tutorials as sent by the server,
 *   in the lazy session or the action starting one
 * @returns {Object[]} the tutorials with the (sanitized) HTML of the messages
 *   of their steps marked up
 */
function markupMessages(tutorials) {
    return tutorials.map((tutorial) => ({
        ...tutorial,
        steps: tutorial.steps.map((step) => ({ ...step, message: markup(step.message) })),
    }));
}

/**
 * Guides the user through the running tutorials. A chapter is the
 * successive steps of the same views (see `TutorialChapter`). In the
 * displayed chapter, the pointer shows the first step not done yet,
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
    /** The engine of the tutorials, loaded the first time some run */
    #engine = null;
    /**
     * Whether some tutorials were run, the ones of the lazy session being
     * outdated then (e.g. by a link starting one)
     */
    #hasRun = false;
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
     * Whether the user is pressing the pointer, the message ending a tutorial
     * waiting for the click (closing it) to end
     */
    #isPointerPressed = false;
    #lazySession = usePlugin(LazySessionPlugin);
    /**
     * The listeners of the user's interactions, added once some tutorials run
     * @type {AbortController | null}
     */
    #listeners = null;
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
            if (step.type === "field" || step.skippable) {
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
    #rpcs = useRpcTracker("web_tutorial.tutorial");
    tutorials = [];
    #updateForAnimation = useThrottleForAnimation(() => this.#update());

    /**
     * Starts the running tutorials of the lazy session, once the web client
     * is ready, only listening to the user once some run; unless the tutorial
     * of a link (?tutorial=<key>, with &expand_messages=1 to open its
     * tooltips) started meanwhile
     */
    setup() {
        if (window.frameElement) {
            return;
        }
        if (router.current.tutorial) {
            const expandMessages = ["1", "true"].includes(String(router.current.expand_messages));
            this.#startFromLink(String(router.current.tutorial), expandMessages);
        }
        this.#lazySession.getValue("running_tutorials", (tutorials) => {
            if (tutorials?.length && !this.#hasRun) {
                this.run(markupMessages(tutorials));
            }
        });
        useListener(rpcBus, "RPC:RESPONSE", ({ detail }) => {
            const { method, model } = detail.data.params || {};
            const isSave = method?.startsWith("web_save") && !detail.error;
            if (model === "web_tutorial.tutorial" && isSave) {
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
            this.#listeners?.abort();
        });
    }

    /**
     * Runs the tutorials instead of the running ones, without reloading the
     * web client: loads their engine and the pointer, and listens to the
     * user, the first time
     * @param {Object[]} tutorials the running tutorials of the user, the
     *   messages of their steps marked up
     */
    async run(tutorials) {
        this.#hasRun = true;
        const Tutorial = await this.#loadEngine();
        if (this.#isDestroyed) {
            return;
        }
        this.tutorials = tutorials.map((data) => new Tutorial(data, this.#orm));
        if (!this.tutorials.length) {
            this.#hidePointer();
            return;
        }
        if (!this.#listeners) {
            this.#listen();
        }
        this.#observer.observe(document, OBSERVED_CHANGES);
        this.#update();
    }

    /**
     * Ends the tutorial for the user: finished or skipped
     * @param {Tutorial} tutorial
     */
    endTutorial(tutorial) {
        this.tutorials = this.tutorials.filter((running) => running !== tutorial);
        tutorial.end();
        if (!this.tutorials.length) {
            this.#hidePointer();
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
            ["expand_messages"]
        );
        for (const { id, expand_messages } of records) {
            const tutorial = this.tutorials.find((running) => running.id === id);
            if (tutorial) {
                tutorial.expandMessages = expand_messages || tutorial.userExpandsMessages;
            }
        }
        this.#update();
    }

    /**
     * Hides the pointer, and stops following the changes of the page, once
     * no tutorial runs
     */
    #hidePointer() {
        this.#observer?.disconnect();
        Object.assign(pointerState, HIDDEN_POINTER);
        this.#pointedStep = null;
    }

    /**
     * Listens to the user's interactions doing the steps, and adds the
     * pointer, updated on any change of the page
     */
    #listen() {
        this.#listeners = new AbortController();
        const { signal } = this.#listeners;
        const handlers = {
            click: (ev) => this.#onClick(ev),
            focusin: (ev) => this.#markFieldDoneBy(ev.target),
            keydown: (ev) => this.#onKeyDown(ev),
            pointerdown: (ev) => this.#onPointerDown(ev),
        };
        for (const [type, handler] of Object.entries(handlers)) {
            window.addEventListener(type, handler, { capture: true, signal });
        }
        for (const type of ["click", "keyup", "pointerup", "pointercancel"]) {
            window.addEventListener(type, () => (this.#isUserInteracting = false), { signal });
        }
        for (const type of ["pointerup", "pointercancel"]) {
            window.addEventListener(type, () => (this.#isPointerPressed = false), { signal });
        }
        this.#overlay.add(TutorialPointer, {}, { sequence: 1100 });
        this.#observer = new MutationObserver(() => this.#updateForAnimation());
    }

    /**
     * Loads the engine of the tutorials, in a bundle, once the web client is
     * ready
     * @returns {Promise<typeof import("@web_tutorial/tutorial/tutorial").Tutorial>}
     */
    #loadEngine() {
        this.#engine ||= (async () => {
            await whenReady();
            if (!odoo.loader.modules.get("@web_tutorial/tutorial/tutorial")) {
                await loadBundle("web_tutorial.tutorial", { css: false });
            }
            this.#domUtils = odoo.loader.modules.get("@web_tutorial/tutorial/utils");
            return odoo.loader.modules.get("@web_tutorial/tutorial/tutorial").Tutorial;
        })();
        return this.#engine;
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
            return {
                actionId: controller.action.id,
                resModel: controller.action.res_model,
                type: controller.view.type,
            };
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
                if (tutorial.endMessage) {
                    this.#showEndMessage(tutorial);
                }
            }
        }
        this.#update();
    }

    /**
     * Shows the message ending the tutorial, once the pointer is released if
     * pressed (e.g. on the field of its last step), not to be closed by the
     * click right after
     * @param {Tutorial} tutorial
     */
    #showEndMessage(tutorial) {
        const show = () =>
            this.#effect.add({
                message: htmlReplaceAll(tutorial.endMessage, "\n", markup`<br>`),
                type: "rainbow_man",
            });
        if (!this.#isPointerPressed) {
            show();
            return;
        }
        let isShown = false;
        const showOnce = () => {
            if (!isShown) {
                isShown = true;
                setTimeout(show);
            }
        };
        for (const type of ["pointerup", "pointercancel"]) {
            window.addEventListener(type, showOnce, { once: true, signal: this.#listeners.signal });
        }
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
        this.#isPointerPressed = true;
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
     * Starts the tutorial of the key for the user (from their progress), on
     * its starting action, whose URL doesn't keep the key
     * @param {string} key
     * @param {boolean} expandMessages whether to open the tooltips of its
     *   steps for the user
     */
    async #startFromLink(key, expandMessages) {
        const action = await this.#orm.call("web_tutorial.tutorial", "start_from_key", [
            key,
            expandMessages,
        ]);
        if (action) {
            await this.#action.doAction(action);
        }
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

/**
 * Starts a tutorial without reloading the web client (see
 * `web_tutorial.tutorial._get_start_action`): runs the tutorials of the user
 * among which it is, then opens its starting action in the app of its menu
 * @param {Object} action
 */
async function startTutorial(action) {
    const tutorialPlugin = usePlugin(TutorialPlugin);
    const actionPlugin = usePlugin(ActionPlugin);
    const menuPlugin = usePlugin(MenuPlugin);
    const { action_id, menu_id, running_tutorials } = action.params;
    await tutorialPlugin.run(markupMessages(running_tutorials));
    const menu = menu_id && menuPlugin.getMenu(menu_id);
    if (menu) {
        await menuPlugin.selectMenu(menu);
    } else {
        await actionPlugin.doAction(action_id, { clearBreadcrumbs: true });
    }
}

registry.category("actions").add("web_tutorial.start", startTutorial);
