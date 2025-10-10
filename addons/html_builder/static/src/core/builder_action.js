/**
 * @typedef { import("../../../../html_editor/static/src/editor").EditorContext } EditorContext
 */

export class BuilderAction {
    static dependencies = [];
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

        this.setup();

        // Preview is enabled by default in non-reload actions,
        // and disabled by default in reload actions.
        this.preview ??= this.reload ? false : true;
        this.withLoadingEffect ??= true;
        this.loadOnClean ??= false;
    }

    /**
     * Called after dependencies and services are assigned.
     * Subclasses override this instead of the constructor.
     */
    setup() {
        // Optional override in subclasses
    }

    prepare(context) {}
    getPriority(context) {}
    /**
     * Apply the action on the editing element.
     * @param {Object} context
     * @param {boolean} context.isPreviewing
     * @param {HTMLElement} context.editingElement
     * @param {any} context.value
     * @param {Object} [context.params]
     */
    apply(context) {}

    /**
     * Return the current value of the action on the element.
     * @param {Object} context
     * @param {HTMLElement} context.editingElement
     * @param {Object} [context.params]
     * @returns {any}
     */
    getValue(context) {}

    /**
     * Whether the action is already applied.
     * @param {Object} context
     * @param {HTMLElement} context.editingElement
     * @param {any} context.value
     * @param {Object} [context.params]
     * @returns {boolean}
     */
    isApplied(context) {}

    /**
     * Clean/reset the value if needed.
     * @param {Object} context
     * @param {boolean} context.isPreviewing
     * @param {HTMLElement} context.editingElement
     * @param {any} context.value
     * @param {Object} [context.params]
     */
    clean(context) {}

    /**
     * Load the options if needed.
     * @param {Object} context
     * @param {HTMLElement} context.editingElement
     */
    async load(context) {}

    /**
     * Check if a method has been overridden.
     * @param {string} method
     * @returns {boolean}
     */
    has(method) {
        const baseMethod = BuilderAction.prototype[method];
        const actualMethod = this.constructor.prototype[method];
        return baseMethod !== actualMethod;
    }
}
