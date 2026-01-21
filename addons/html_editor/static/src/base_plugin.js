/**
 * @typedef { import("./editor").Editor } Editor
 * @typedef { import("./editor").EditorContext } EditorContext
 */

export class BasePlugin {
    static id = "";
    static dependencies = [];
    static shared = [];
    static defaultConfig = {};

    /** @type {Partial<import("plugins").Resources>} */
    resources;

    /**
     * @param { EditorContext } context
     */
    constructor(context) {
        this.window = context.document.defaultView;
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

    destroy() {
        for (const cleanup of this._cleanups) {
            cleanup();
        }
        this.isDestroyed = true;
    }
}
