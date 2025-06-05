export class BuilderAction {
    static dependencies = [];
    constructor(plugin, dependencies) {
        this.window = plugin.window;
        this.document = plugin.document;
        this.editable = plugin.editable;
        this.dependencies = dependencies;
        this.services = plugin.services;
        this.config = plugin.config;
        this.getResource = plugin.getResource.bind(plugin);
        this.dispatchTo = plugin.dispatchTo.bind(plugin);
        this.delegateTo = plugin.delegateTo.bind(plugin);

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
