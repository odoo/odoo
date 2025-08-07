export class Action {
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

    /** When provided, this component is mounted for this action. UI/UX of action is fully managed by the component */
    get component() {
        return this.explicitDefinition.component;
    }

    /** When provided, action.component is conditionally picked based on this condition. When condition is false, the usual UI/UX of action from other explicit definitions is chosen */
    get componentCondition() {
        return typeof this.explicitDefinition.componentCondition === "function"
            ? this.explicitDefinition.componentCondition(this._component)
            : this.explicitDefinition.componentCondition ?? true;
    }

    /** Props to pass to the component of this action. */
    get componentProps() {
        return this.explicitDefinition.componentProps?.(this._component, this);
    }

    /** If set, this is considered as a danger (destructive) action. */
    get danger() {
        return typeof this.explicitDefinition.danger === "function"
            ? this.explicitDefinition.danger(this._component)
            : this.explicitDefinition.danger;
    }

    /** Condition to disable the button of this action (but still display it). */
    get disabledCondition() {
        return this.explicitDefinition.disabledCondition?.(this._component);
    }

    /** Determines whether this action opens a dropdown on selection. Value is shaped { template, menuClass } */
    get dropdown() {
        return this.explicitDefinition.dropdown;
    }

    /** Determines whether this action has a keyboard hotkey to trigger the onSelected */
    get hotkey() {
        return typeof this.explicitDefinition.hotkey === "function"
            ? this.explicitDefinition.hotkey(this._component)
            : this.explicitDefinition.hotkey;
    }

    /**
     * Icon for the button this action.
     * - When a string, this is considered an icon as classname (.fa and .oi).
     * - When an object with property `template`, this is an icon rendered in template.
     *   Template params are provided in `params` and passed to template as a `t-set="templateParams"`
     */
    get icon() {
        return typeof this.explicitDefinition.icon === "function"
            ? this.explicitDefinition.icon(this._component)
            : this.explicitDefinition.icon;
    }

    /**
     * Large icon for the button this action.
     * - When a string, this is considered an icon as classname (.fa and .oi).
     * - When an object with property `template`, this is an icon rendered in template.
     *   Template params are provided in `params` and passed to template as a `t-set="templateParams"`
     */
    get iconLarge() {
        return typeof this.explicitDefinition.iconLarge === "function"
            ? this.explicitDefinition.iconLarge(this._component)
            : this.explicitDefinition.iconLarge ?? this.icon;
    }

    /** Name of this action, displayed to the user. */
    get name() {
        return typeof this.explicitDefinition.name === "function"
            ? this.explicitDefinition.name(this._component)
            : this.explicitDefinition.name;
    }

    /** Action to execute when this action is selected */
    onSelected(ev) {
        return this.explicitDefinition.onSelected?.(this._component, this, ev);
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
