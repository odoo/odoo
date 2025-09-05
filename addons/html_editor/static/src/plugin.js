import { isProtected, isProtecting, isUnprotecting } from "./utils/dom_info";

export const isValidTargetForDomListener = (target) =>
    !isProtecting(target) && (!isProtected(target) || isUnprotecting(target));

/**
 * @typedef { import("./editor").Editor } Editor
 * @typedef { import("./plugin_sets").SharedMethods } SharedMethods
 */

export class Plugin {
    static id = "";
    static dependencies = [];
    static shared = [];
    static defaultConfig = {};

    /**
     * @param {Editor['document']} document
     * @param {Editor['editable']} editable
     * @param {SharedMethods} dependencies
     * @param {import("./editor").EditorConfig} config
     * @param {*} services
     */
    constructor(document, editable, dependencies, config, services) {
        /** @type { Document } **/
        this.document = document;
        /** @type { Window } */
        this.window = document.defaultView;
        /** @type { HTMLElement } **/
        this.editable = editable;
        /** @type { EditorConfig } **/
        this.config = config;
        this.services = services;
        /** @type { SharedMethods } **/
        this.dependencies = dependencies;
        this._cleanups = [];
        /**
         * The resources aggregated from all the plugins by the editor.
         */
        this._resources = null; // set before start
        this.isDestroyed = false;
    }

    setup() {}

    isValidTargetForDomListener(ev) {
        return isValidTargetForDomListener(ev.target);
    }

    /**
     * Add an event listener on a given target, that will only be executed if
     * the target is valid (unless `isGlobal` is true), and ensure it is removed
     * when we destroy the editor.
     *
     * @param {Element} target
     * @param {string} eventName
     * @param {function(Event):void} fn
     * @param {boolean} [capture=false] `useCapture` flag of `addEventListener`
     * @param {boolean} [isGlobal=false] if true, don't check target validity
     */
    addDomListener(target, eventName, fn, capture = false, isGlobal = false) {
        const handler = (ev) => {
            if (isGlobal || this.isValidTargetForDomListener(ev)) {
                fn?.call(this, ev);
            }
        };
        target.addEventListener(eventName, handler, capture);
        this._cleanups.push(() => target.removeEventListener(eventName, handler, capture));
    }

    /**
     * Add an event listener on the editor's document, and ensure it is removed
     * when we destroy the editor.
     *
     * @todo Use this function to avoid iframe problems.
     *
     * @param {string} eventName
     * @param {function(Event):void} fn
     * @param {boolean} [capture=false] `useCapture` flag of `addEventListener`
     */
    addGlobalDomListener(eventName, fn, capture = false) {
        this.addDomListener(this.document, eventName, fn, capture, true);
    }

    /**
     * @param {string} resourceId
     * @returns {Array}
     */
    getResource(resourceId) {
        return this._resources[resourceId] || [];
    }

    /**
     * Execute all the callbacks registered under resourceId (which ends with
     * "_handlers" by convention) with the given arguments.
     *
     * This function can be thought as an event dispatcher, calling the handlers
     * with `args` as the payload.
     *
     * Example:
     * ```js
     * this.dispatchTo("my_event_handlers", arg1, arg2);
     * ```
     *
     * @param {string} resourceId
     * @param  {...any} args The arguments to pass to the handlers.
     */
    dispatchTo(resourceId, ...args) {
        this.getResource(resourceId).forEach((handler) => handler(...args));
    }

    /**
     * Execute a series of callbacks registered under resourceId (which ends
     * with "_overrides" by convention) until one of them returns a truthy
     * value, and returns whether this happened.
     *
     * Warning: not all callbacks will necessarily be run. Consider using
     * {@link dispatchTo} instead if all callbacks must be executed.
     *
     * Semantically, this function indicates that, even though there's code to
     * handle an operation the default way, it can be **delegated** to a
     * callback that handles a specific case, in which case it **overrides**
     * that default behavior.
     *
     * The registered "_overrides" callbacks must return a truthy value to
     * signal the operation has been handled.
     *
     * It is the caller's responsibility to stop the execution when this
     * function returns true.
     *
     * Example:
     * ```js
     * if (this.delegateTo("some_operation_overrides", arg1, arg2)) {
     *   return;
     * }
     * // code that does some operation the default way - executed unless overridden
     * ```
     *
     * @param {string} resourceId
     * @param  {...any} args The arguments to pass to the overrides.
     * @returns {boolean} Whether one of the overrides returned a truthy value.
     */
    delegateTo(resourceId, ...args) {
        return this.getResource(resourceId).some((fn) => fn(...args));
    }

    destroy() {
        for (const cleanup of this._cleanups) {
            cleanup();
        }
        this.isDestroyed = true;
    }
}
