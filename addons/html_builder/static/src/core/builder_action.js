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
        this.preview = true;

        this.apply = this.apply.bind(this);
        this.isApplied = this.isApplied.bind(this);
        this.getPriority = this.getPriority.bind(this);
        this.setup = this.setup.bind(this);
        this.getValue = this.getValue.bind(this);
        this.clean = this.clean.bind(this);
        this.load = this.load.bind(this);
        this.loadOnClean = this.loadOnClean.bind(this);
        this.prepare = this.prepare.bind(this);
        this.setup();
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
     */
    getValue(context) {}

    /**
     * Whether the action is already applied.
     * @param {Object} context
     * @param {HTMLElement} context.editingElement
     * @param {any} context.value
     * @param {Object} [context.params]
     */
    isApplied() {}

    /**
     * Clean/reset the value if needed.
     * @param {Object} context
     * @param {HTMLElement} context.editingElement
     */
    clean(context) {}

    /**
     * Load the options if needed.
     * @param {Object} context
     * @param {HTMLElement} context.editingElement
     */
    async load(context) {}

    loadOnClean(context) {}

    /**
     * Check if a method has been overridden.
     * @param {string} method
     */
    has(method) {
        const baseMethod = BuilderAction.prototype[method];
        const actualMethod = this.constructor.prototype[method];
        return baseMethod !== actualMethod;
    }
}
