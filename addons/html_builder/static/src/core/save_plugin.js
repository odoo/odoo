import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { isZWS } from "@html_editor/utils/dom_info";
import { _t } from "@web/core/l10n/translation";
import { EDITOR_MUTATION_TYPES } from "@html_editor/core/dom_observer_plugin";
import { escapeTextNodes } from "@html_builder/utils/escaping";
import { selectElements } from "@html_editor/utils/dom_traversal";

/**
 * Clone `el` and run the handlers needed to get it ready for save
 *
 * @param {Plugin} plugin any plugin, needed to access the resources
 * @param {HTMLElement} el
 * @param {Object} options passed to `clean_for_save_processors`
 * @returns {HTMLElement}
 */
// This is not a shared of the save plugin, because that plugin is not
// available in mass mailing (which needs this function to save snippets)
export function prepareElementForSave(plugin, el, options = {}) {
    const cloneEl = el.cloneNode(true);
    const cleanedEl = plugin.processThrough("clean_for_save_processors", cloneEl, options);
    escapeTextNodes(cleanedEl);
    return cleanedEl;
}

/** @typedef {import("plugins").CSSSelector} CSSSelector */
/**
 * @typedef { Object } SaveShared
 * @property { SavePlugin['save'] } save
 * @property { SavePlugin['ignoreDirty'] } ignoreDirty
 * @property { SavePlugin['setDirtyElement'] } setDirtyElement
 */

/**
 * @typedef {((el?: HTMLElement) => void)[]} on_saved_handlers
 * @typedef {((el?: HTMLElement, groupedEls?: Object.<string, HTMLElement[]>) => Promise<void>)[]} on_will_save_handlers
 * Called before the save process.
 *
 * @typedef {(() => Promise<boolean>)[]} on_ready_to_save_document_handlers
 * Called concurrently as part of the save process.
 *
 * @typedef {{
 *      selector: CSSSelector;
 *      dirtyClass: string;
 *      match?: "closest" | "self";
 * }[]} dirty_trackers
 *
 * A mutation marks the element matching `selector` with `dirtyClass`. Declare one to be
 * notified of changes to an element that cannot be saved as view arch, and pair it with
 * `on_ready_to_save_document_handlers` to persist it another way. Declaring a tracker does
 * not make the element savable: only `.o_savable` / `o_dirty` feeds the arch saving pipeline.
 *
 * `match` defaults to `"closest"`, which walks up the ancestors of the mutated element. Use
 * `"self"` when the state you persist lives in the element's own attributes, so that changes
 * inside it, such as editing a branded field in a descendant, do not mark it dirty. Not
 * literally self: `handleMutations` resolves an added or removed node to its parent, so a
 * direct child appearing or disappearing marks the element too.
 */

export class SavePlugin extends Plugin {
    static id = "savePlugin";
    static shared = ["save", "ignoreDirty", "setDirtyElement"];
    static dependencies = ["history", "domReferenceMap"];

    /** @type {import("plugins").BuilderResources} */
    resources = {
        on_pending_mutations_staged_handlers: this.handleMutations.bind(this),
        on_editor_started_handlers: this.startObserving.bind(this),
        // Resource definitions:
        clean_for_save_processors: (rootEl) => {
            rootEl.classList.remove("o_dirty");
            this.removeZWSPFromEmbeddedFields(rootEl);
            return rootEl;
        },
        dirty_trackers: { selector: ".o_savable", dirtyClass: "o_dirty" },
        // Do not change the sequence of this resource, it must stay the first
        // one to avoid marking dirty when not needed during the drag and drop.
        on_prepare_drag_handlers: withSequence(0, this.ignoreDirty.bind(this)),
    };

    removeZWSPFromEmbeddedFields(rootEl) {
        // Remove zero-width spaces left by DeletePlugin.fillEmptyInlines on
        // embedded fields to prevent saving blank model fields.
        const selector = '[data-oe-model]:not([data-oe-model="ir.ui.view"])';
        for (const el of selectElements(rootEl, selector)) {
            if (isZWS(el)) {
                el.innerHTML = "";
            }
        }
    }

    setup() {
        this.canObserve = false;
        this.dirtyTrackers = this.getResource("dirty_trackers");
    }

    async save({ shouldSkipAfterSaveHandlers = async () => true } = {}) {
        let skipAfterSaveHandlers;
        try {
            await Promise.all(this.trigger("on_will_save_handlers", this.editable));
            await Promise.all(this.trigger("on_ready_to_save_document_handlers"));
            this.dependencies.history.reset();
            skipAfterSaveHandlers = await shouldSkipAfterSaveHandlers();
        } catch (error) {
            if (error.exceptionName === "odoo.exceptions.ValidationError") {
                this.services.notification.add(_t("Previous values restored."), {
                    title: _t("One or more fields were not valid"),
                    type: "warning",
                });
            } else {
                throw error;
            }
        } finally {
            if (!skipAfterSaveHandlers) {
                this.trigger("on_saved_handlers");
            }
        }
    }

    startObserving() {
        this.canObserve = true;
    }
    /**
     * Handles the flag of the closest savable element to the mutation as dirty
     *
     * @param {import("@html_editor/core/dom_observer_plugin").SerializedMutation[]} mutations - The observed mutations
     */
    handleMutations(mutations) {
        if (!this.canObserve) {
            return;
        }
        for (const mutation of mutations) {
            if (mutation.isAutomatic) {
                continue;
            }
            if (
                mutation.type === EDITOR_MUTATION_TYPES.ATTRIBUTES &&
                mutation.attributeName === "contenteditable"
            ) {
                continue;
            }
            let targetId = mutation.nodeId;
            // TODO: Wouldn't doing this only for "remove" be enough?
            if (
                [EDITOR_MUTATION_TYPES.ADD, EDITOR_MUTATION_TYPES.REMOVE].includes(mutation.type) &&
                mutation.parentNodeId
            ) {
                targetId = mutation.parentNodeId;
            }
            let targetEl = this.dependencies.domReferenceMap.getNodeById(targetId);
            if (!targetEl.isConnected) {
                continue;
            }
            if (targetEl.nodeType !== Node.ELEMENT_NODE) {
                targetEl = targetEl.parentElement;
            }
            if (!targetEl) {
                continue;
            }
            for (const { selector, dirtyClass, match } of this.dirtyTrackers) {
                const dirtyEl =
                    match === "self"
                        ? targetEl.matches(selector) && targetEl
                        : targetEl.closest(selector);
                if (
                    !dirtyEl ||
                    dirtyEl.classList.contains(dirtyClass) ||
                    dirtyEl.hasAttribute("data-oe-readonly")
                ) {
                    continue;
                }
                dirtyEl.classList.add(dirtyClass);
            }
        }
    }

    /**
     * Prevents elements to be marked as dirty until it is reactivated with the
     * returned callback.
     *
     * @returns {Function}
     */
    ignoreDirty() {
        this.canObserve = false;
        return () => {
            this.canObserve = true;
        };
    }

    setDirtyElement(el) {
        el.classList.add("o_dirty");
    }
}
