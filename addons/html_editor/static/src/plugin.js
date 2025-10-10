import { isProtected, isProtecting, isUnprotecting } from "./utils/dom_info";

export const isValidTargetForDomListener = (target) =>
    !isProtecting(target) && (!isProtected(target) || isUnprotecting(target));

/**
 * @typedef { import("./editor").Editor } Editor
 * @typedef { import("./editor").EditorContext } EditorContext
 * @typedef { import("./plugin_sets").SharedMethods } SharedMethods
 */

export class Plugin {
    static id = "";
    static dependencies = [];
    static shared = [];
    static defaultConfig = {};

    /**
     * @param { EditorContext } context
     */
    constructor(context) {
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
        /** @type { EditorContext['dispatchTo'] } **/
        this.dispatchTo = context.dispatchTo;
        /** @type { EditorContext['delegateTo'] } **/
        this.delegateTo = context.delegateTo;

        this._cleanups = [];
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

    destroy() {
        for (const cleanup of this._cleanups) {
            cleanup();
        }
        this.isDestroyed = true;
    }
}
