export class DiscussActionDefinition {
    /** User-defined explicit definition of this action */
    explicitDefinition;
    /** Component in which the action is being used */
    _component;
    /** Unique id of this action. */
    id;

    constructor(component, id, explicitDefinition) {
        this.explicitDefinition = explicitDefinition;
        this.id = id;
        this._component = component;
    }

    /** If set, this is considered as a danger (destructive) action. */
    get danger() {
        return typeof this.explicitDefinition.danger === "function"
            ? this.explicitDefinition.danger(this._component)
            : this.explicitDefinition.danger;
    }

    /** Determines the order of this action (smaller first). */
    get sequence() {
        return typeof this.explicitDefinition.sequence === "function"
            ? this.explicitDefinition.sequence(this._component)
            : this.explicitDefinition.sequence;
    }

    /** Component setup to execute when this action is registered. */
    setup(...args) {
        return this.explicitDefinition.setup?.(...args);
    }

    /** If set, this is considered as a success (high-commitment positive) action. */
    get success() {
        return typeof this.explicitDefinition.success === "function"
            ? this.explicitDefinition.success(this._component)
            : this.explicitDefinition.success;
    }
}
