import { useComponent } from "@odoo/owl";
import { Reactive } from "@web/core/utils/reactive";

/** @typedef {import("@odoo/owl").Component} Component */

/**
 * @typedef {Object} ActionDefinition
 * @property {string|(comp: Component) => string} [btnClass]
 * @property {Component} [component]
 * @property {boolean|(comp: Component) => boolean} [componentCondition=true]
 * @property {(comp: Component) => Component<Props, Env>} [componentProps]
 * @property {boolean|(comp: Component) => boolean} [danger]
 * @property {boolean|(comp: Component) => boolean} [disabledCondition]
 * @property {boolean} [dropdown]
 * @property {string|(comp: Component) => string} [hotkey]
 * @property {string|(comp: Component) => string} [icon]
 * @property {string|(comp: Component) => string} [iconLarge]
 * @property {boolean|(comp: Component) => boolean} [isActive]
 * @property {string|(comp: Component) => string} [name]
 * @property {(component: Component, ev: Event) => void} [onSelected]
 * @property {number|(comp: Component) => number} [sequence]
 * @property {boolean|(comp: Component) => boolean} [sequenceGroup]
 * @property {boolean|(comp: Component) => boolean} [sequenceQuick]
 * @property {() => void} [setup]
 * @property {boolean|(comp: Component) => boolean} [success]
 */

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

    get btnClass() {
        return typeof this.explicitDefinition.btnClass === "function"
            ? this.explicitDefinition.btnClass.call(this, this._component)
            : this.explicitDefinition.btnClass;
    }

    /** When provided, this component is mounted for this action. UI/UX of action is fully managed by the component */
    get component() {
        return this.explicitDefinition.component;
    }

    /** When provided, action.component is conditionally picked based on this condition. When condition is false, the usual UI/UX of action from other explicit definitions is chosen */
    get componentCondition() {
        return typeof this.explicitDefinition.componentCondition === "function"
            ? this.explicitDefinition.componentCondition.call(this, this._component)
            : this.explicitDefinition.componentCondition ?? true;
    }

    /** Props to pass to the component of this action. */
    get componentProps() {
        return this.explicitDefinition.componentProps?.call(this, this._component, this);
    }

    /** If set, this is considered as a danger (destructive) action. */
    get danger() {
        return typeof this.explicitDefinition.danger === "function"
            ? this.explicitDefinition.danger.call(this, this._component)
            : this.explicitDefinition.danger;
    }

    /** Condition to disable the button of this action (but still display it). */
    get disabledCondition() {
        return this.explicitDefinition.disabledCondition?.call(this, this._component);
    }

    /** Determines whether this action opens a dropdown on selection. Value is shaped { template, menuClass } */
    get dropdown() {
        return this.explicitDefinition.dropdown;
    }

    /** Determines whether this action has a keyboard hotkey to trigger the onSelected */
    get hotkey() {
        return typeof this.explicitDefinition.hotkey === "function"
            ? this.explicitDefinition.hotkey.call(this, this._component)
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
            ? this.explicitDefinition.icon.call(this, this._component)
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
            ? this.explicitDefinition.iconLarge.call(this, this._component)
            : this.explicitDefinition.iconLarge ?? this.icon;
    }

    /** States whether this action is currently active. */
    get isActive() {
        return typeof this.explicitDefinition.isActive === "function"
            ? this.explicitDefinition.isActive.call(this, this._component)
            : this.explicitDefinition.isActive;
    }

    /** Name of this action, displayed to the user. */
    get name() {
        return typeof this.explicitDefinition.name === "function"
            ? this.explicitDefinition.name.call(this, this._component)
            : this.explicitDefinition.name;
    }

    /** Action to execute when this action is selected */
    onSelected(ev) {
        return this.explicitDefinition.onSelected?.call(this, this._component, this, ev);
    }

    /** Determines the order of this action (smaller first). */
    get sequence() {
        return typeof this.explicitDefinition.sequence === "function"
            ? this.explicitDefinition.sequence.call(this, this._component)
            : this.explicitDefinition.sequence;
    }

    /** Component setup to execute when this action is registered. */
    setup() {
        const component = useComponent();
        return this.explicitDefinition.setup?.call(this, component);
    }

    /** If set, this is considered as a success (high-commitment positive) action. */
    get success() {
        return typeof this.explicitDefinition.success === "function"
            ? this.explicitDefinition.success.call(this, this._component)
            : this.explicitDefinition.success;
    }
}

export class UseActions extends Reactive {
    ActionClass = Action;
    component;
    transformedActions;

    constructor(component, transformedActions) {
        super();
        this.component = component;
        this.transformedActions = transformedActions;
    }

    get actions() {
        const actions = this.transformedActions
            .filter((action) => action.condition)
            .sort((a1, a2) => a1.sequence - a2.sequence);
        if (actions.length > 0) {
            actions.at(0).isFirst = true;
            actions.at(-1).isLast = true;
        }
        return actions;
    }

    get partition() {
        const actions = this.transformedActions.filter((action) => action.condition);
        const quick = actions
            .filter((a) => a.sequenceQuick)
            .sort((a1, a2) => a1.sequenceQuick - a2.sequenceQuick);
        const grouped = actions.filter((a) => a.sequenceGroup);
        const groups = {};
        for (const a of grouped) {
            if (!(a.sequenceGroup in groups)) {
                groups[a.sequenceGroup] = [];
            }
            groups[a.sequenceGroup].push(a);
        }
        const sortedGroups = Object.entries(groups).sort(
            ([groupId1], [groupId2]) => groupId1 - groupId2
        );
        for (const [, actions] of sortedGroups) {
            actions.sort((a1, a2) => a1.sequence - a2.sequence);
        }
        const group = sortedGroups.map(([groupId, actions]) => actions);
        const other = actions
            .filter((a) => !a.sequenceQuick && !a.sequenceGroup)
            .sort((a1, a2) => a1.sequence - a2.sequence);
        return { quick, group, other };
    }
}
