import { isRecord, STORE_SYM } from "@mail/model/misc";
import { Component, markRaw, proxy, signal, useScope } from "@odoo/owl";
import { DropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useService } from "@web/core/utils/hooks";
import { markEventHandled } from "@web/core/utils/misc";
import { Reactive } from "@web/core/utils/reactive";

export const ACTION_TAGS = Object.freeze({
    DANGER: "DANGER",
    SUCCESS: "SUCCESS",
    PRIMARY: "PRIMARY",
    IMPORTANT_BADGE: "IMPORTANT_BADGE",
    WARNING_BADGE: "WARNING_BADGE",
    CALL_ACTION_TRACKED: "CALL_ACTION_TRACKED",
    CALL_LAYOUT: "CALL_LAYOUT",
    JOIN_LEAVE_CALL: "JOIN_LEAVE_CALL",
});

/** @typedef {import("@odoo/owl").Component} Component */
/** @typedef {import("@mail/model/record").Record} Record */
/** @typedef {Component|Record} ActionOwner */

/**
 * @typedef {Object} ActionRootRefParam
 * @property {import("@odoo/owl").Signal<HTMLElement>} [rootRef] Signal pointing at the owner's root
 *   element, used to anchor popovers and `querySelector` action buttons. The concrete element type is up
 *   to the caller.
 */

/**
 * @template Action_T
 * @typedef {Object} ActionPanelCloseSpecificParams
 * @property {Action_T} nextActiveAction
 */

/**
 * @template Action_T
 * @typedef {{actionPanels: Action_T[], quick: Action_T[], group: Array<Action_T[]>, other: Action_T[]}} PartitionedActions
 */

/**
 * @template Action_T
 * @template UseActions_T
 * @typedef {ActionRootRefParam & {actions: UseActions_T, action: Action_T, renderingContext: import("@mail/core/common/action_list").Action, store: import("models").Store, owner: ActionOwner}} ActionParams
 */

/**
 * @template ActionParams_T
 * @template Action_T
 * @typedef {Object} ActionDefinition
 * @property {(params: ActionParams_T & ActionPanelCloseSpecificParams<Action_T>) => void} [actionPanelClose]
 * @property {Component} [actionPanelComponent]
 * @property {(params: ActionParams_T) => Object} [actionPanelComponentProps]
 * @property {(params: ActionParams_T) => string} [actionPanelName]
 * @property {(params: ActionParams_T) => void} [actionPanelOpen]
 * @property {string|(params: ActionParams_T) => string} [actionPanelOuterClass]
 * @property {boolean|(params: ActionParams_T) => boolean} [badge]
 * @property {string|(params: ActionParams_T) => string} [badgeIcon]
 * @property {string|(params: ActionParams_T) => string} [badgeText]
 * @property {Object|(params: ActionParams_T) => Object} [btnAttrs]
 * @property {string|(params: ActionParams_T) => string} [btnClass]
 * @property {Component} [component]
 * @property {boolean|(params: ActionParams_T) => boolean} [componentCondition=true]
 * @property {(params: ActionParams_T) => Component<Props, Env>} [componentProps]
 * @property {boolean|(params: ActionParams_T) => boolean} [condition=true]
 * @property {boolean|(params: ActionParams_T) => boolean} [disabledCondition]
 * @property {boolean} [dropdown]
 * @property {Component|(params: ActionParams_T) => Component} [dropdownComponent]
 * @property {Object|(params: ActionParams_T) => Object} [dropdownComponentProps]
 * @property {string|(params: ActionParams_T) => string} [dropdownMenuClass]
 * @property {string|(params: ActionParams_T) => string} [dropdownPosition]
 * @property {DropdownState|(params: ActionParams_T) => DropdownState} [dropdownState]
 * @property {string|(params: ActionParams_T) => string} [dropdownTemplate]
 * @property {Object|(params: ActionParams_T) => Object} [dropdownTemplateParams]
 * @property {boolean|(params: ActionParams_T) => boolean} [hasBtnBg]
 * @property {string|(params: ActionParams_T) => string} [hotkey]
 * @property {string|(params: ActionParams_T) => string} [icon]
 * @property {boolean|(params: ActionParams_T) => boolean} [inlineName=false]
 * @property {boolean|(params: ActionParams_T) => boolean} [isActive]
 * @property {string|(params: ActionParams_T) => string} [name]
 * @property {string|(params: ActionParams_T) => string} [nameClass]
 * @property {(params: ActionParams_T, ev: Event) => void} [onSelected]
 * @property {number|(params: ActionParams_T) => number} [sequence]
 * @property {boolean|(params: ActionParams_T) => boolean} [sequenceGroup]
 * @property {boolean|(params: ActionParams_T) => boolean} [sequenceQuick]
 * @property {(params: ActionParams_T) => void} [setup]
 * @property {string|string[]|(params: ActionParams_T) => string|string[]} [tags]
 */

/** @template ActionParams_T */
export class Action {
    /** @type {UseActions} */
    actions;
    /** @type {ActionDefinition<ActionParams_T>}  User-defined explicit definition of this action */
    definition;
    /** @type {ActionOwner} Entity that is using this action */
    owner;
    /**
     * When this action opens a popover, must save usePopover() in this attribute, i.e. action.popover = usePopover().
     * Useful for action that open an action panel in some contexts and popovers in others. See @actionPanel
     *
     * @type {import("@web/core/popover/popover_hook").PopoverHookReturnType}
     */
    popover = null;
    /** @type {string} Unique id of this action. */
    id;
    /**
     * This should be set by the component rendering the action so that it can be used
     * as a parameter of the different functions of the action.
     *
     * @type {null|() => import("@mail/core/common/action_list").Action}
     */
    renderingContext = markRaw({ fn: null });
    /** @type {import("@odoo/owl").Signal<HTMLElement>} */
    rootRef;
    /** @type {import("models").Store} */
    store;
    actionRef = signal(null);

    /**
     * param `store` is required for actions made with new Action() by hand in components and outside component.setup()
     *
     * @param {Object} params0
     * @param {UseActionClass_T} [params0.actions]
     * @param {ActionOwner} params0.owner
     * @param {string} params0.id
     * @param {ActionDefinition<ActionParams, Action>} params0.definition
     * @param {import("models").Store} [params0.store]
     * @param {import("@odoo/owl").Signal<HTMLElement>} [params0.rootRef] @see ActionRootRefParam
     */
    constructor({ actions, owner, id, definition, store, rootRef }) {
        this.actions = actions;
        this.definition = definition;
        this.id = id;
        this.owner = owner;
        this.rootRef = rootRef;
        this.store =
            store ??
            (owner[STORE_SYM] ? owner : isRecord(owner) ? owner.store : useService("mail.store"));
    }

    get params() {
        return {
            actions: this.actions,
            action: this,
            store: this.store,
            owner: this.owner,
            rootRef: this.rootRef,
            renderingContext: this.renderingContext.fn?.(),
        };
    }

    /** Determines whether this action is a one time effect or can be toggled (on or off). */
    get actionPanel() {
        return Boolean(this.definition.actionPanelComponent);
    }

    /**
     * Closes the action panel of this action.
     *
     * @param {Object} [param0={}]
     * @param {Action} [param0.nextActiveAction] When action panel is closed by opening another panel,
     *   this param tells which is the next active action
     * @param {boolean} [param0.closeAll] When true, all action panels in the stack are closed without returning to a previous panel
     */
    actionPanelClose({ nextActiveAction, closeAll = false } = {}) {
        this.popover?.close();
        if (this.actions) {
            if (closeAll) {
                this.actions.actionStack = [];
                this.actions.activeAction = null;
            } else {
                this.actions.activeAction = this.actions.actionStack.pop();
            }
        }
        this.definition.actionPanelClose?.call(
            this,
            Object.assign(this.params, { nextActiveAction })
        );
    }

    /** Optional component that is used as action panel of this component, i.e. when action is active. */
    get actionPanelComponent() {
        return this.definition.actionPanelComponent;
    }

    /** Condition to display the action panel component of this action. */
    get actionPanelComponentCondition() {
        return this.isActive && this.actionPanelComponent && this.condition && !this.popover;
    }

    /** Props to pass to the action panel component of this action. */
    get actionPanelComponentProps() {
        return {
            close: (opts) => this.actionPanelClose(opts),
            ...(this.definition.actionPanelComponentProps?.call(this, this.params) ?? {}),
        };
    }

    /** @param {Action} action @returns {string|undefined} */
    _actionPanelName(action) {}
    /** Name of this action, displayed to the user. */
    get actionPanelName() {
        return (
            this._actionPanelName(this.params) ??
            (typeof this.definition.actionPanelName === "function"
                ? this.definition.actionPanelName.call(this, this.params)
                : this.definition.actionPanelName ?? this.name)
        );
    }

    /**
     * Opens action panel of this action.
     *
     * @param {object} [param0]
     * @param {boolean} [param0.keepPrevious] Whether the previous action
     * should be kept so that closing the current action goes back
     * to the previous one.
     * */
    actionPanelOpen({ keepPrevious } = {}) {
        if (this.actions) {
            if (this.actions.activeAction) {
                if (keepPrevious) {
                    this.actions.actionStack.push(this.actions.activeAction);
                } else {
                    this.actions.activeAction.actionPanelClose({ nextActiveAction: this });
                }
            }
            this.actions.activeAction = this;
        }
        this.definition.actionPanelOpen?.call(this, this.params);
    }

    get actionPanelOuterClass() {
        return typeof this.definition.actionPanelOuterClass === "function"
            ? this.definition.actionPanelOuterClass.call(this, this.params)
            : this.definition.actionPanelOuterClass;
    }

    /** @param {Action} action @returns {boolean|undefined} */
    _badge(action) {}
    /** Condition for showing badge on this action */
    get badge() {
        return (
            this._badge(this.params) ??
            (typeof this.definition.badge === "function"
                ? this.definition.badge.call(this, this.params)
                : this.definition.badge)
        );
    }

    /** @param {Action} action @returns {string|undefined} */
    _badgeIcon(action) {}
    /** When action shows badge @see badge this property tells the icon inside badge */
    get badgeIcon() {
        return (
            this._badgeIcon(this.params) ??
            (typeof this.definition.badgeIcon === "function"
                ? this.definition.badgeIcon.call(this, this.params)
                : this.definition.badgeIcon)
        );
    }

    /** @param {Action} action @returns {string|undefined} */
    _badgeText(action) {}
    /** When action shows badge @see badge this property tells the text inside badge. */
    get badgeText() {
        return (
            this._badgeText(this.params) ??
            (typeof this.definition.badgeText === "function"
                ? this.definition.badgeText.call(this, this.params)
                : this.definition.badgeText)
        );
    }

    /** @param {Action} action @returns {Object|undefined} */
    _btnAttrs(action) {}
    get btnAttrs() {
        return (
            this._btnAttrs(this.params) ??
            (typeof this.definition.btnAttrs === "function"
                ? this.definition.btnAttrs.call(this, this.params)
                : this.definition.btnAttrs)
        );
    }

    /** @param {Action} action @returns {string|undefined} */
    _btnClass(action) {}
    get btnClass() {
        return (
            this._btnClass(this.params) ??
            (typeof this.definition.btnClass === "function"
                ? this.definition.btnClass.call(this, this.params)
                : this.definition.btnClass)
        );
    }

    /** @param {Action} action @returns {Component|undefined} */
    _component(action) {}
    /** When provided, this component is mounted for this action. UI/UX of action is fully managed by the component */
    get component() {
        return this._component(this.params) ?? this.definition.component;
    }

    /** @param {Action} action @returns {boolean|undefined} */
    _componentCondition(action) {}
    /** When provided, action.component is conditionally picked based on this condition. When condition is false, the usual UI/UX of action from other explicit definitions is chosen */
    get componentCondition() {
        return (
            this._componentCondition(this.params) ??
            (typeof this.definition.componentCondition === "function"
                ? this.definition.componentCondition.call(this, this.params)
                : this.definition.componentCondition ?? true)
        );
    }

    /** @param {Action} action @returns {Object|undefined} */
    _componentProps(action) {}
    /** Props to pass to the component of this action. */
    get componentProps() {
        return (
            this._componentProps(this.params) ??
            this.definition.componentProps?.call(this, this.params)
        );
    }

    /** @param {Action} action @returns {boolean|undefined} */
    _condition(action) {}
    /** Condition for availability of this action */
    get condition() {
        return (
            this._condition(this.params) ??
            (typeof this.definition.condition === "function"
                ? this.definition.condition.call(this, this.params)
                : this.definition.condition ?? true)
        );
    }

    /** @param {Action} action @returns {boolean|undefined} */
    _disabledCondition(action) {}
    /** Condition to disable the button of this action (but still display it). */
    get disabledCondition() {
        return Boolean(
            this._disabledCondition(this.params) ??
                (typeof this.definition.disabledCondition === "function"
                    ? this.definition.disabledCondition.call(this, this.params)
                    : this.definition.disabledCondition)
        );
    }

    /** @param {Action} action @returns {boolean|undefined} */
    _dropdown(action) {}
    /** Determines whether this action opens a dropdown on selection. */
    get dropdown() {
        return (
            this._dropdown(this.params) ??
            (typeof this.definition.dropdown === "function"
                ? this.definition.dropdown.call(this, this.params)
                : this.definition.dropdown)
        );
    }

    /** @param {Action} action @returns {Component|undefined} */
    _dropdownComponent(action) {}
    /** When action is a dropdown @see dropdown, this determines an optional component to use for the content slot */
    get dropdownComponent() {
        return (
            this._dropdownComponent(this.params) ??
            (typeof this.definition.dropdownComponent === "function" &&
            Object.getPrototypeOf(this.definition.dropdownComponent) !== Component
                ? this.definition.dropdownComponent.call(this, this.params)
                : this.definition.dropdownComponent)
        );
    }

    /** @param {Action} action @returns {Object|undefined} */
    _dropdownComponentProps(action) {}
    /** When action is a dropdown @see dropdown, this determines optional props to pass to component of the content slot of dropdown. */
    get dropdownComponentProps() {
        return (
            this._dropdownComponentProps(this.params) ??
            (typeof this.definition.dropdownComponentProps === "function"
                ? this.definition.dropdownComponentProps.call(this, this.params)
                : this.definition.dropdownComponentProps)
        );
    }

    /** @param {Action} action @returns {string|undefined} */
    _dropdownMenuClass(action) {}
    /** When action is a dropdown @see dropdown, this determines an optional menu class for the dropdown, in addition to default dropdown menu classes */
    get dropdownMenuClass() {
        return (
            this._dropdownMenuClass(this.params) ??
            (typeof this.definition.dropdownMenuClass === "function"
                ? this.definition.dropdownMenuClass.call(this, this.params)
                : this.definition.dropdownMenuClass)
        );
    }

    /** @param {Action} action @returns {string|undefined} */
    _dropdownPosition(action) {}
    /** When action is a dropdown @see dropdown, this determines the preferred position of the dropdown */
    get dropdownPosition() {
        return (
            this._dropdownPosition(this.params) ??
            (typeof this.definition.dropdownPosition === "function"
                ? this.definition.dropdownPosition.call(this, this.params)
                : this.definition.dropdownPosition)
        );
    }

    /** @param {Action} action @returns {DropdownState|undefined} */
    _dropdownState(action) {}
    /** When action is a dropdown @see dropdown, this determines the preferred position of the dropdown */
    get dropdownState() {
        return (
            this._dropdownState(this.params) ??
            (typeof this.definition.dropdownState === "function"
                ? this.definition.dropdownState.call(this, this.params)
                : this.definition.dropdownState)
        );
    }

    /** @param {Action} action @returns {string|undefined} */
    _dropdownTemplate(action) {}
    /** When action is a dropdown @see dropdown, this determines an optional template to use for the content slot */
    get dropdownTemplate() {
        return (
            this._dropdownTemplate(this.params) ??
            (typeof this.definition.dropdownTemplate === "function"
                ? this.definition.dropdownTemplate.call(this, this.params)
                : this.definition.dropdownTemplate)
        );
    }

    /** @param {Action} action @returns {Object|undefined} */
    _dropdownTemplateParams(action) {}
    /**
     * When action is a dropdown @see dropdown, this determines optional params to pass to template of the content slot of dropdown.
     * The params are provided to template in object `templateParams` with named parameters as given by explicit definition.
     * For example: `{ myParam1: 1 }` is retrieved in template with `templateParams.myParam1`.
     */
    get dropdownTemplateParams() {
        return (
            this._dropdownTemplateParams(this.params) ??
            (typeof this.definition.dropdownTemplateParams === "function"
                ? this.definition.dropdownTemplateParams.call(this, this.params)
                : this.definition.dropdownTemplateParams)
        );
    }

    /** @param {Action} action @returns {boolean|undefined} */
    _hasBtnBg(action) {}
    get hasBtnBg() {
        return (
            this._hasBtnBg(this.params) ??
            (typeof this.definition.hasBtnBg === "function"
                ? this.definition.hasBtnBg.call(this, this.params)
                : this.definition.hasBtnBg)
        );
    }

    /** @param {Action} action @returns {string|undefined} */
    _hotkey(action) {}
    /** Determines whether this action has a keyboard hotkey to trigger the onSelected */
    get hotkey() {
        return (
            this._hotkey(this.params) ??
            (typeof this.definition.hotkey === "function"
                ? this.definition.hotkey.call(this, this.params)
                : this.definition.hotkey)
        );
    }

    /** @param {Action} action @returns {string|Object|undefined} */
    _icon(action) {}
    /**
     * Icon for the button this action.
     * - When a string, this is considered an icon as classname (.fa and .oi).
     * - When an object with property `template`, this is an icon rendered in template.
     *   Template params are provided in `params` and passed to template as a `t-set="templateParams"`
     */
    get icon() {
        return (
            this._icon(this.params) ??
            (typeof this.definition.icon === "function"
                ? this.definition.icon.call(this, this.params)
                : this.definition.icon)
        );
    }

    /** @param {Action} action @returns {string|undefined} */
    _inlineName(action) {}
    /** If set, when action is used in inline, shows action name in addition to icon. */
    get inlineName() {
        return (
            this._inlineName(this.params) ??
            (typeof this.definition.inlineName === "function"
                ? this.definition.inlineName.call(this, this.params)
                : this.definition.inlineName) ??
            false
        );
    }

    /** @param {Action} action @returns {boolean|undefined} */
    _isActive(action) {}
    /** States whether this action is currently active. */
    get isActive() {
        if (this.actions && this.actionPanel) {
            return this.id === this.actions.activeAction?.id;
        }
        return (
            this._isActive(this.params) ??
            (typeof this.definition.isActive === "function"
                ? this.definition.isActive.call(this, this.params)
                : this.definition.isActive)
        );
    }

    /** @param {Action} action @returns {string|undefined} */
    _name(action) {}
    /** Name of this action, displayed to the user. */
    get name() {
        return (
            this._name(this.params) ??
            (typeof this.definition.name === "function"
                ? this.definition.name.call(this, this.params)
                : this.definition.name)
        );
    }

    /** ClassName on name of this action */
    get nameClass() {
        return typeof this.definition.nameClass === "function"
            ? this.definition.nameClass.call(this, this.params)
            : this.definition.nameClass;
    }

    /** @param {Action} action @param {Event} ev @returns {true|undefined} */
    _onSelected(action, ev) {}
    /** Action to execute when this action is selected @param {Event} ev */
    onSelected(ev, { keepPrevious } = {}) {
        if (ev) {
            markEventHandled(ev, "Action.onSelected");
        }
        if (this.actionPanel) {
            if (this.isActive) {
                this.actionPanelClose();
            } else {
                this.actionPanelOpen({ keepPrevious });
            }
        }
        return (
            this._onSelected(this.params, ev) ??
            this.definition.onSelected?.call(this, this.params, ev)
        );
    }

    /** @param {Action} action @returns {number|undefined} */
    _sequence(action) {}
    /** Determines the order of this action (smaller first). */
    get sequence() {
        return (
            this._sequence(this.params) ??
            (typeof this.definition.sequence === "function"
                ? this.definition.sequence.call(this, this.params)
                : this.definition.sequence)
        );
    }

    /** @param {Action} action @returns {number|undefined} */
    _sequenceGroup(action) {}
    get sequenceGroup() {
        return (
            this._sequenceGroup(this.params) ??
            (typeof this.definition.sequenceGroup === "function"
                ? this.definition.sequenceGroup.call(this, this.params)
                : this.definition.sequenceGroup)
        );
    }

    /** @param {Action} action @returns {number|undefined} */
    _sequenceQuick(action) {}
    get sequenceQuick() {
        return (
            this._sequenceQuick(this.params) ??
            (typeof this.definition.sequenceQuick === "function"
                ? this.definition.sequenceQuick.call(this, this.params)
                : this.definition.sequenceQuick)
        );
    }

    setRenderingContext(renderingContext) {
        this.renderingContext.fn = () => renderingContext;
    }

    /** @param {Action} action @returns {true|undefined} */
    _setup(action) {}
    /** setup is executed when the owner is being setup. */
    setup() {
        return this._setup(this.params) ?? this.definition.setup?.call(this, this.params);
    }

    /** @param {Action} action @returns {string|string[]|undefined} */
    _tags(action) {}
    /** If set, list of tags of this action. */
    get tags() {
        const res =
            this._tags(this.params) ??
            (typeof this.definition.tags === "function"
                ? this.definition.tags.call(this, this.params)
                : this.definition.tags);
        return Array.isArray(res) ? res : [res];
    }

    get tagClassNames() {
        return this.tags.map((tag) => `o-tag-${tag}`).join(" ");
    }

    unsetRenderingContext() {
        this.renderingContext.fn = null;
    }
}

/**
 * @template ActionParams_T
 * @template Action_T
 */
export class UseActions extends Reactive {
    /** @type {Action_T} */
    ActionClass = Action;
    /** @type {Component} */
    component;
    /** @type {Map<string, Action_T>} */
    moreActions = new Map();
    /** @type {Action<ActionParams_T>[]} */
    transformedActions;
    /** @type {import("models").Store} */
    store;
    /** @type {Action_T[]} */
    actionStack = [];
    /** @type {Action_T} */
    activeAction = null;

    /**
     * @param {Component} component
     * @param {import("models").Store} store
     * @param {Action_T[]} transformedActions
     */
    constructor(component, store, transformedActions) {
        super();
        this.component = component;
        this.store = store;
        this.transformedActions = transformedActions;
    }

    /**
     * @typedef {Object} MoreActionSpecificDefinition
     * @property {Action_T[]|Array<Action_T[]>} actions
     */
    /** @typedef {ActionDefinition<ActionParams_T, Action_T> & MoreActionSpecificDefinition} MoreActionDefinition */
    /**
     * @param {MoreActionDefinition} [data]
     * @returns {Action_T}
     */
    more(actionsParams = {}, data = {}, id) {
        let moreAction = this.moreActions.get(id);
        if (moreAction) {
            moreAction = this.moreActions.get(id);
            moreAction.definition.actions = data.actions;
        } else {
            moreAction = new this.ActionClass({
                ...actionsParams,
                owner: this.component,
                id: `more-action:${id}`,
                definition: {
                    ...data,
                    dropdown: true,
                    dropdownState: new DropdownState(),
                    icon: data?.icon ?? "oi oi-ellipsis-v",
                    isActive: ({ action }) => action.dropdownState.isOpen,
                    isMoreAction: true,
                    sequence: data.sequence ?? 1000,
                },
                store: this.store,
            });
            this.moreActions.set(data.id, moreAction);
        }
        return moreAction;
    }

    /** @returns {Action_T[]} */
    get actions() {
        const actions = this.transformedActions
            .filter((action) => action.condition)
            .sort((a1, a2) => a1.sequence - a2.sequence);
        return actions;
    }

    /** @return {PartitionedActions<Action_T>} */
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
        const groupedActionPanels = Object.groupBy(
            actions.filter((a) => a.actionPanel),
            (a) => (a.sequenceQuick ? "quick" : "other")
        );
        groupedActionPanels.quick?.sort((a1, a2) => a1.sequenceQuick - a2.sequenceQuick);
        groupedActionPanels.other?.sort((a1, a2) => a1.sequence - a2.sequence);
        const actionPanels = (groupedActionPanels.other ?? []).concat(
            groupedActionPanels.quick ?? []
        );
        return { actionPanels, quick, group, other };
    }
}

/**
 * @template {typeof UseActions} UseActionClass_T
 * @param {Object} param0
 * @param {typeof UseActionClass_T} param0.UseActionClass
 * @param {Component} params0.component
 * @returns {InstanceType<UseActionClass_T>}
 */
function useActionState({ UseActionClass, component }) {
    return proxy(new UseActionClass(component, useService("mail.store")));
}

/**
 * @template ActionParams_T
 * @template Action_T
 * @param {import("@web/core/registry").Registry<ActionDefinition<ActionParams_T, Action_T>>} actionRegistry
 * @param {typeof UseActionClass_T} UseActionClass
 * @param {typeof Action_T} ActionClass
 * @param {ActionParams_T & ActionRootRefParam} actionClassParams Forwarded to the `ActionClass`
 *   constructor; may carry a `rootRef` (@see ActionRootRefParam) shared by all action types.
 * @returns {InstanceType<UseActionClass_T>}
 */
export function useAction(actionRegistry, UseActionClass, ActionClass, actionClassParams) {
    const component = useScope().component;
    const actions = useActionState({ UseActionClass, component });
    /** @type {Action_T[]} */
    const transformedActions = actionRegistry.getEntries().map(
        ([id, definition]) =>
            new ActionClass({
                actions,
                owner: component,
                id,
                definition,
                ...actionClassParams,
            })
    );
    for (const action of transformedActions) {
        action.setup();
    }
    actions.transformedActions = transformedActions;
    return actions;
}
