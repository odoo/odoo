import { BasePlugin } from "@html_editor/base_plugin";
import { isProtected, isProtecting, isUnprotecting } from "./utils/dom_info";

export const isValidTargetForDomListener = (target) =>
    !isProtecting(target) && (!isProtected(target) || isUnprotecting(target));

/**
 * @typedef { import("./editor").Editor } Editor
 * @typedef { import("./editor").EditorContext } EditorContext
 */

export class Plugin extends BasePlugin {
    constructor(context) {
        super(context);
        this.window = context.document.defaultView;
        /** @type { EditorContext['editable'] } **/
        this.editable = context.editable;
        /** @type { EditorContext['document'] } **/
        this.document = context.document;
    }

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
}
