import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

/**
 * @typedef { Object } DirtMarkShared
 * @property { DirtMarkPlugin['setDirty'] } setDirty
 * @property { DirtMarkPlugin['queryDirtys'] } queryDirtys
 */

/**
 * @typedef {{
 *  id: string,
 *  setDirtyOnMutation?: (record: import("@html_editor/core/history_plugin").HistoryMutationRecord) => HTMLElement?,
 *  save?: (el: HTMLElement) => Promise<void>,
 *  saveAll?: (els: HTMLElement[]) => Promise<void>,
 * }[]} dirt_marks
 */

export class DirtMarkPlugin extends Plugin {
    static id = "dirtMark";
    static dependencies = ["history"];
    static shared = ["setDirty", "queryDirtys"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        start_edition_handlers: () => (this.canObserve = true),
        handleNewRecords: (records) => {
            if (this.canObserve) {
                for (const record of records) {
                    for (const { id, setDirtyOnMutation } of this.getResource("dirt_marks")) {
                        const el = setDirtyOnMutation?.(record);
                        if (el) {
                            this.elsToDirty[id] ??= new Set();
                            this.elsToDirty[id].add(el);
                        }
                    }
                }
            }
        },
        normalize_handlers: (_, stepType) => {
            if (stepType !== "original") {
                this.elsToDirty = {};
                return;
            }
            for (const [id, els] of Object.entries(this.elsToDirty)) {
                for (const el of els) {
                    this.setDirty(id, el);
                }
            }
        },
        attribute_change_processors: this.attributeChangeProcessors.bind(this),

        // Do not change the sequence of this resource, it must stay the first
        // one to avoid marking dirty when not needed during the drag and drop.
        on_prepare_drag_handlers: withSequence(0, this.ignoreDirty.bind(this)),

        clean_for_save_handlers: ({ root }) => {
            for (const { id } of this.getResource("dirt_marks")) {
                const dirtAttribute = `data-dirty-${id}`;
                for (const el of selectElements(root, `[${dirtAttribute}]`)) {
                    el.removeAttribute(dirtAttribute);
                }
            }
        },
        save_handlers: () =>
            Promise.all(
                this.getResource("dirt_marks").map(({ id, save, saveAll }) => {
                    if (save) {
                        return Promise.all(
                            this.queryDirtys(id).map(({ el, setClean }) => save(el).then(setClean))
                        );
                    } else if (saveAll) {
                        const dirtys = this.queryDirtys(id);
                        if (dirtys.length) {
                            return saveAll(dirtys);
                        }
                    }
                })
            ),
    };

    elsToDirty = {};

    /**
     * Prevents elements to be marked as dirty until it is reactivated with the
     * returned callback.
     *
     * @returns {Function}
     */
    ignoreDirty() {
        this.canObserve = false;
        return () => (this.canObserve = true);
    }

    /**
     * @param {string} id
     * @param {HTMLElement} el
     */
    setDirty(id, el) {
        const dirtAttribute = `data-dirty-${id}`;
        let current = el.getAttribute(dirtAttribute);
        if (current === "always") {
            return;
        }
        current = current ? parseInt(current) : 0;
        el.setAttribute(dirtAttribute, current < 0 ? "always" : current + 1);
    }

    /**
     * @param {string} id
     * @returns {{el: HTMLElement, setClean: () => void}[]}
     */
    queryDirtys(id) {
        const dirtAttribute = `data-dirty-${id}`;
        const setClean = (el) =>
            this.dependencies.history.ignoreDOMMutations(() => el.removeAttribute(dirtAttribute));
        const dirtyEls = selectElements(this.editable, `[${dirtAttribute}]`);
        return [...dirtyEls].map((el) => ({ el, setClean: () => setClean(el) }));
    }

    attributeChangeProcessors({ target, attributeName, oldValue, value, reverse }, { stepType }) {
        if (attributeName.startsWith("data-dirty-")) {
            const currentValue = target.getAttribute(attributeName);
            if (currentValue === "always") {
                return "always";
            }
            const count = currentValue ? parseInt(currentValue) : 0;
            const newCount =
                count + { undo: -1, redo: 1, restore: reverse ? -1 : 1 }[stepType] ?? 0;
            return newCount || null;
        } else {
            return value;
        }
    }
}

registry.category("website-plugins").add(DirtMarkPlugin.id, DirtMarkPlugin);
registry.category("translation-plugins").add(DirtMarkPlugin.id, DirtMarkPlugin);
