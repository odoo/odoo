import { useComponent, useEnv } from "@web/owl2/utils";
import { Component, onWillDestroy } from "@odoo/owl";
import { useDomState } from "@html_builder/core/utils";

/**
 * @typedef { import("../../../../html_editor/static/src/editor").EditorContext } EditorContext
 */

export function useIsActiveItem() {
    const env = useEnv();
    const listenedKeys = new Set();

    function isActive(itemId) {
        const isActiveFn = env.dependencyManager.get(itemId)?.isActive;
        if (!isActiveFn) {
            return false;
        }
        return isActiveFn();
    }

    const getState = () => {
        const newState = {};
        for (const itemId of listenedKeys) {
            newState[itemId] = isActive(itemId);
        }
        return newState;
    };
    const state = useDomState(getState);
    const listener = () => {
        const newState = getState();
        Object.assign(state, newState);
    };
    env.dependencyManager.addEventListener("dependency-updated", listener);
    onWillDestroy(() => {
        env.dependencyManager.removeEventListener("dependency-updated", listener);
    });
    return function isActiveItem(itemId) {
        listenedKeys.add(itemId);
        if (state[itemId] === undefined) {
            return isActive(itemId);
        }
        return state[itemId];
    };
}

export class BaseOptionComponent extends Component {
    static components = {};
    static props = {};
    static template = "";
    // When `editableOnly` is set to false, the element does not need to be in
    // an editable area and the checks are therefore lighter. (= previous
    // data-no-check/noCheck)
    static editableOnly = true;

    setup() {
        /** @type {EditorContext} */
        const context = this.env.editor.shared.builderOptions.getBuilderOptionContext(
            this.constructor
        );
        /** @type { EditorContext['document'] } **/
        this.document = context.document;
        this.window = context.document.defaultView;
        /** @type { EditorContext['editable'] } **/
        this.editable = context.editable;
        /** @type { EditorContext['config'] } **/
        this.config = context.config;
        /** @type { EditorContext['services'] } **/
        this.services = context.services;
        /** @type { EditorContext['dependencies'] } **/
        this.dependencies = context.dependencies;
        /** @type { EditorContext['getResource'] } **/
        this.getResource = context.getResource;
        /** @type { EditorContext['trigger'] } **/
        this.trigger = context.trigger;
        /** @type { EditorContext['triggerAsync'] } **/
        this.triggerAsync = context.triggerAsync;
        /** @type { EditorContext['delegateTo'] } **/
        this.delegateTo = context.delegateTo;
        /** @type { EditorContext['processThrough'] } **/
        this.processThrough = context.processThrough;
        /** @type { EditorContext['checkPredicates'] } **/
        this.checkPredicates = context.checkPredicates;

        this.isActiveItem = useIsActiveItem();
        const comp = useComponent();
        const editor = comp.env.editor;

        if (!comp.constructor.components) {
            comp.constructor.components = {};
        }
        const Components = editor.shared.builderComponents.getComponents();
        Object.assign(comp.constructor.components, Components);
    }
    /**
     * Check if the given items are active.
     *
     * Map over all items to listen for any reactive value changes.
     *
     * @param {string[]} itemIds - The IDs of the items to check.
     * @returns {boolean} - True if the item is active, false otherwise.
     */
    isActiveItems(itemIds) {
        return itemIds.map((i) => this.isActiveItem(i)).find(Boolean) || false;
    }
}
