export class Plugin {
    static id = "";
    static dependencies = [];
    static shared = [];
    static defaultConfig = {};

    resources;

    constructor(context) {
        this.config = context.config;
        this.services = context.services;
        this.dependencies = context.dependencies;
        this.getResource = context.getResource;
        this.trigger = context.trigger;
        this.triggerAsync = context.triggerAsync;
        this.delegateTo = context.delegateTo;
        this.processRules = context.processRules;
        this.processThrough = context.processThrough;
        this.checkPredicates = context.checkPredicates;

        this._cleanups = [];
        this.isDestroyed = false;

        this.assignShared();
    }

    setup() {}

    assignShared() {
        const shortHands = new Map();
        const reservedKeys = new Set();
        let current = this;
        while (current !== null) {
            for (const key of Reflect.ownKeys(current)) {
                reservedKeys.add(key);
            }
            current = Object.getPrototypeOf(current);
        }
        for (const sharedFunctions of Object.values(this.dependencies)) {
            for (const [functionName, functionObject] of Object.entries(sharedFunctions)) {
                if (!reservedKeys.has(functionName)) {
                    reservedKeys.add(functionName);
                    shortHands.set(functionName, functionObject);
                } else {
                    // Overlap, use `this.dependencies[plugin][sharedFunction]`
                    shortHands.delete(functionName);
                }
            }
        }
        for (const [functionName, functionObject] of shortHands) {
            this[functionName] = functionObject;
        }
    }

    destroy() {
        for (const cleanup of this._cleanups) {
            cleanup();
        }
        this.isDestroyed = true;
    }
}
