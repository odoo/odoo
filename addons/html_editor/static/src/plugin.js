import { isProtected, isProtecting, isUnprotecting } from "./utils/dom_info";

/**
 * @typedef { import("./editor").Editor } Editor
 * @typedef { import("./plugin_sets").SharedMethods } SharedMethods
 */

export class Plugin {
    static id = "";
    static dependencies = [];
    static shared = [];

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
        return !isProtecting(ev.target) && (!isProtected(ev.target) || isUnprotecting(ev.target));
    }

    addDomListener(target, eventName, fn, capture = false) {
        const handler = (ev) => {
            if (this.isValidTargetForDomListener(ev)) {
                fn?.call(this, ev);
            }
        };
        target.addEventListener(eventName, handler, capture);
        this._cleanups.push(() => target.removeEventListener(eventName, handler, capture));
    }

    /**
     * @param {string} resourceId
     * @returns {Array}
     */
    getResource(resourceId) {
        return this._resources[resourceId] || [];
    }

    /**
     * Execute the functions registered under resourceId with the given
     * arguments.
     *
     * This function is meant to enhance code readability by clearly expressing
     * its intent.
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
     * Execute a series of functions until one of them returns a truthy value.
     *
     * This function is meant to enhance code readability by clearly expressing
     * its intent.
     *
     * A command "delegates" its execution to one of the overriding functions,
     * which return a truthy value to signal it has been handled.
     *
     * It is the the caller's responsability to stop the execution when this
     * function returns true.
     *
     * Example:
     * ```js
     * if (this.delegateTo("my_command_overrides", arg1, arg2)) {
     *   return;
     * }
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
