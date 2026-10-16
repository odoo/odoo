import { useAncestors } from "@mail/core/common/ancestor_plugin";
import { isRecord, STORE_SYM } from "@mail/model/misc";
import { computedShallowEqual } from "@mail/utils/common/signal";
import { Component, computed, markRaw, proxy, signal, t, useProps, useScope, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { DropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useService } from "@web/core/utils/hooks";
import { markEventHandled } from "@web/core/utils/misc";

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

export const ACTION_GROUP_TAGS = Object.freeze({
    ACTION_PANELS: "ACTION_PANELS",
});

export const IS_ACTION_DEFINITION_SYM = Symbol("isActionDefinition");
export const IS_ACTION_GROUP_DESCRIPTION_SYM = Symbol("isActionGroupDescription");

/** @param {undefined|T|T[]} val @returns {T[]} @template T */
function toArray(val) {
    if (!val) {
        return [];
    }
    return Array.isArray(val) ? val : [val];
}

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
 * @typedef {{panelActions: Action_T[], quick: Action_T[], group: Array<Action_T[]>, other: Action_T[]}} PartitionedActions
 */

/**
 * @template Action_T
 * @template UseActions_T
 * @typedef {ActionRootRefParam & {actions: UseActions_T, action: Action_T, ancestors: Readonly<Record<string, any>>, store: import("models").Store, owner: ActionOwner}} ActionParams
 */

/** @typedef {number} ActionGroupId id of group is a number that also represents its sequence between groups! */

/**
 * Kinds of container in which the panel of an action is shown, @see PanelContainer:
 * - PANEL: in the panel of the owner of the action, e.g. beside or in place of the conversation;
 * - DROPDOWN: in a dropdown of the button of the action;
 * - POPOVER: in a popover on the button of the action;
 * - DIALOG: in a dialog.
 */
export const PANEL_CONTAINER_TYPE = Object.freeze({
    PANEL: "panel",
    DROPDOWN: "dropdown",
    POPOVER: "popover",
    DIALOG: "dialog",
});

/**
 * Where the panel of an action is shown, which the place that mounts the action decides, @see
 * ActionList (`panelContainer` prop). The other keys than `type` are options of how the container
 * looks, e.g. the position of a dropdown.
 *
 * @typedef {typeof PANEL_CONTAINER_TYPE[keyof typeof PANEL_CONTAINER_TYPE]} PanelContainerType
 * @typedef {{ type: PanelContainerType, arrow?: boolean, contentClass?: string, fixedPosition?: boolean, menuClass?: string, popoverClass?: string, position?: string, target?: HTMLElement, title?: string }} PanelContainer
 */
/** @type {PanelContainer} */
export const PANEL = Object.freeze({ type: PANEL_CONTAINER_TYPE.PANEL });

/** Dialog showing the panel of an action, @see PanelContainer */
class ActionPanelDialog extends Component {
    static components = { Dialog };
    static template = xml`
        <Dialog size="'md'" title="this.props.title" footer="false" contentClass="'o-bg-body ' + (this.props.contentClass ?? '')" bodyClass="'p-3'">
            <t t-component="this.props.component" t-props="this.props.componentProps"/>
        </Dialog>
    `;
    props = useProps({
        close: t.function().optional(),
        component: t.component(),
        componentProps: t.object(),
        contentClass: t.string().optional(),
        title: t.string().optional(),
    });
}

/**
 * What an action opens when it is selected, wherever it is shown, @see PanelContainer. The
 * component can describe its content with static properties, so that the place showing the action
 * picks a container that suits it:
 * - `compact`: the content is small, e.g. a short form, so that a place with a large panel can
 *   rather show it on the button of the action, e.g. in a popover;
 * - `menu`: the content is a menu, e.g. a list of choices, which opens in a dropdown of the button
 *   of the action unless the place picks another container.
 *
 * @template ActionParams_T
 * @template Action_T
 * @typedef {Object} PanelDefinition
 * @property {typeof Component & { compact?: boolean, menu?: boolean }} component
 * @property {(params: ActionParams_T) => Object} [props]
 * @property {TranslatedString|(params: ActionParams_T) => TranslatedString} [name] defaults to
 *   the name of the action
 * @property {(params: ActionParams_T) => void} [onOpen]
 * @property {(params: ActionParams_T & ActionPanelCloseSpecificParams<Action_T>) => void} [onClose]
 */

/**
 * Options of closing the panel of an action, e.g. from its content, @see Panel
 *
 * @typedef {Object} PanelCloseOptions
 * @property {boolean} [closeAll] Whether to also close the panels kept to go back to, instead of
 *   going back to the previous one
 */

/**
 * The panel of an action as shown in a container, @see Action.getPanel
 *
 * @typedef {{ action: Action, component: typeof Component, name: string, props: { close: (options?: PanelCloseOptions) => void } & Object }} Panel
 */

/** @typedef {{ name: string?, tags?: string|string[] }} ActionGroupDescriptionDefinition */
/** @typedef {ActionGroupDescriptionDefinition & {id: ActionGroupId, tags: string[] }} ActionGroupDescription */

/**
 * @template ActionParams_T
 * @template Action_T
 * @typedef {Object} ActionDefinition
 * @property {boolean|(params: ActionParams_T) => boolean} [availableOffline]
 * @property {boolean|(params: ActionParams_T) => boolean} [badge]
 * @property {string|(params: ActionParams_T) => string} [badgeIcon]
 * @property {string|(params: ActionParams_T) => string} [badgeIconClass]
 * @property {string|(params: ActionParams_T) => string} [badgeText]
 * @property {Component} [extraContentComponent]
 * @property {(params: ActionParams_T) => Component<Props, Env>} [extraContentComponentProps]
 * @property {boolean|(params: ActionParams_T) => boolean} [condition=true]
 * @property {boolean|(params: ActionParams_T) => boolean} [disabledCondition]
 * @property {Component} [extraContentComponent]
 * @property {(params: ActionParams_T) => Object} [extraContentComponentProps]
 * @property {boolean|(params: ActionParams_T) => boolean} [hasBtnBg]
 * @property {string|(params: ActionParams_T) => string} [hotkey]
 * @property {string|(params: ActionParams_T) => string} [icon]
 * @property {string|(params: ActionParams_T) => string} [iconClass]
 * @property {boolean|(params: ActionParams_T) => boolean} [isActive]
 * @property {TranslatedString|((params: ActionParams_T) => TranslatedString)} [name]
 * @property {string|(params: ActionParams_T) => string} [nameClass]
 * @property {(params: ActionParams_T, ev: Event) => void} [onSelected]
 * @property {PanelDefinition<ActionParams_T, Action_T>} [panel]
 * @property {number|(params: ActionParams_T) => number} [sequence]
 * @property {ActionGroupId|(params: ActionParams_T) => ActionGroupId} [sequenceGroup]
 * @property {number|(params: ActionParams_T) => number} [sequenceQuick]
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
    /** @type {Readonly<Record<string, any>>} Named ancestors of the owner, @see useAncestors */
    ancestors;
    /** @type {string} Unique id of this action. */
    id;
    /** @type {import("@odoo/owl").Signal<HTMLElement>} */
    rootRef;
    /** @type {import("models").Store} */
    store;
    actionRef = signal.ref();
    /** Closes the popover or the dialog showing the panel, @see openPanel. Not reactive. */
    overlay = markRaw({ close: undefined });

    /**
     * param `store` is required for actions made with new Action() by hand in components and outside component.setup()
     *
     * @param {Object} params0
     * @param {UseActionClass_T} [params0.actions]
     * @param {Readonly<Record<string, any>>} [params0.ancestors] Named ancestors of the owner,
     *   defaults to the ones of `actions`. Required for actions made with new Action() by hand
     *   in components that depend on the ancestors.
     * @param {ActionOwner} params0.owner
     * @param {string} params0.id
     * @param {ActionDefinition<ActionParams, Action>} params0.definition
     * @param {import("models").Store} [params0.store]
     * @param {import("@odoo/owl").Signal<HTMLElement>} [params0.rootRef] @see ActionRootRefParam
     */
    constructor({ actions, ancestors, owner, id, definition, store, rootRef }) {
        this.actions = actions;
        this.ancestors = ancestors ?? actions?.ancestors ?? {};
        this.definition = definition;
        this.id = id;
        this.owner = owner;
        this.rootRef = rootRef;
        this.store =
            store ??
            (owner[STORE_SYM] ? owner : isRecord(owner) ? owner.store : useService("mail.store"));
        // Memoize the hot per-action getters as owl computeds: a reactive
        // change then only re-evaluates the actions that actually read it,
        // instead of every action of the owner on every render.
        this._conditionComputed = computed(() => this._computeCondition());
        this._sequenceComputed = computed(() => this._computeSequence());
        this._sequenceGroupComputed = computed(() => this._computeSequenceGroup());
        this._sequenceQuickComputed = computed(() => this._computeSequenceQuick());
        /** Open state of the panel when its container is not the panel of the owner, @see PANEL */
        this.overlayState = new DropdownState({
            onOpen: () => this._onOverlayOpen(),
            onClose: () => this._onOverlayClose(),
        });
    }

    get params() {
        return {
            actions: this.actions,
            action: this,
            ancestors: this.ancestors,
            store: this.store,
            owner: this.owner,
            rootRef: this.rootRef,
        };
    }

    /** Whether this action opens a panel, @see PanelDefinition */
    get hasPanel() {
        return Boolean(this.definition.panel);
    }

    /** @returns {Panel|undefined} */
    getPanel() {
        const definition = this.definition.panel;
        if (!definition) {
            return undefined;
        }
        return {
            action: this,
            component: definition.component,
            name:
                (typeof definition.name === "function"
                    ? definition.name.call(this, this.params)
                    : definition.name) ?? this.name,
            props: {
                close: ({ closeAll } = {}) => this.closePanel({ closeAll }),
                ...definition.props?.call(this, this.params),
            },
        };
    }

    /**
     * Opens the panel of this action in the given container, by default in the panel of its
     * owner. A dropdown shows the panel by itself, from the open state of the panel.
     *
     * @param {object} [param0]
     * @param {PanelContainer} [param0.container] Container picked by the place showing the action,
     *   when the action is selected there, @see PanelContainer
     * @param {boolean} [param0.keepPrevious] Whether the panel shown in the panel of the owner
     *   should be kept so that closing this one goes back to it.
     */
    openPanel({ container = PANEL, keepPrevious } = {}) {
        if (container.type !== PANEL.type) {
            this.overlayState.open();
            this.overlay.close = this._openOverlay(container);
            return;
        }
        if (this.actions) {
            const panelAction = this.actions.panelAction;
            if (panelAction?.id === this.id) {
                return;
            }
            if (panelAction) {
                if (keepPrevious) {
                    this.actions.panelStack.push(panelAction);
                } else {
                    panelAction.closePanel({ nextActiveAction: this });
                }
            }
            this.actions.panelAction = this;
        }
        this.definition.panel?.onOpen?.call(this, this.params);
    }

    /**
     * Closes the panel of this action.
     *
     * @param {PanelCloseOptions & { nextActiveAction?: Action }} [param0={}]
     * @param {Action} [param0.nextActiveAction] When the panel is closed by opening another one,
     *   the action of the other panel
     */
    closePanel({ nextActiveAction, closeAll = false } = {}) {
        if (this.overlayState.isOpen) {
            this.overlayState.close();
            return;
        }
        if (this.actions) {
            if (closeAll) {
                this.actions.panelStack = [];
                this.actions.panelAction = null;
            } else {
                this.actions.panelAction = this.actions.panelStack.pop() ?? null;
            }
        }
        this.definition.panel?.onClose?.call(
            this,
            Object.assign(this.params, { nextActiveAction })
        );
    }

    /**
     * Shows the panel of this action in a popover or a dialog, @see openPanel.
     *
     * @param {PanelContainer} container
     * @returns {(() => void)|undefined} closes what was opened
     */
    _openOverlay(container) {
        const { popover, dialog } = this.store.env.services;
        const panel = this.getPanel();
        const onClose = () => {
            if (this.overlayState.isOpen) {
                this.overlayState.close();
            }
        };
        if (container.type === PANEL_CONTAINER_TYPE.POPOVER) {
            return popover.add(container.target ?? this.actionRef(), panel.component, panel.props, {
                arrow: container.arrow,
                fixedPosition: container.fixedPosition,
                onClose,
                popoverClass: container.popoverClass,
                position: container.position,
            });
        }
        if (container.type === PANEL_CONTAINER_TYPE.DIALOG) {
            return dialog.add(
                ActionPanelDialog,
                {
                    component: panel.component,
                    componentProps: panel.props,
                    contentClass: container.contentClass,
                    title: container.title ?? panel.name,
                },
                { onClose }
            );
        }
    }

    _onOverlayOpen() {
        this.definition.panel?.onOpen?.call(this, this.params);
    }

    _onOverlayClose() {
        const close = this.overlay.close;
        this.overlay.close = undefined;
        close?.();
        this.definition.panel?.onClose?.call(this, this.params);
    }

    /** @param {Action} action @returns {boolean|undefined} */
    _availableOffline(action) {}
    /** Whether this action stays usable while offline, i.e. its button is not disabled then. */
    get availableOffline() {
        return (
            this._availableOffline(this.params) ??
            (typeof this.definition.availableOffline === "function"
                ? this.definition.availableOffline.call(this, this.params)
                : this.definition.availableOffline)
        );
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
    _badgeIconClass(action) {}
    /** When action shows badge @see badge this property tells the class of the icon inside badge */
    get badgeIconClass() {
        return (
            this._badgeIconClass(this.params) ??
            (typeof this.definition.badgeIconClass === "function"
                ? this.definition.badgeIconClass.call(this, this.params)
                : this.definition.badgeIconClass)
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

    /** @param {Action} action @returns {boolean|undefined} */
    _condition(action) {}
    _computeCondition() {
        return (
            this._condition(this.params) ??
            (typeof this.definition.condition === "function"
                ? this.definition.condition.call(this, this.params)
                : this.definition.condition ?? true)
        );
    }
    /** Condition for availability of this action */
    get condition() {
        return this._conditionComputed();
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

    /** @param {Action} action @returns {Component|undefined} */
    _extraContentComponent(action) {}
    /** When action needs a small widget on the action button (toggle, checkbox, etc), this allows loading an extra widget that gets aligned to the right */
    get extraContentComponent() {
        return this._extraContentComponent(this.params) ?? this.definition.extraContentComponent;
    }

    /** @param {Action} action @returns {Object|undefined} */
    _extraContentComponentProps(action) {}
    /** When action needs a small widget on the action button (toggle, checkbox, etc), this determines optional props to pass to the widget. */
    get extraContentComponentProps() {
        return (
            this._extraContentComponentProps(this.params) ??
            this.definition.extraContentComponentProps?.call(this, this.params)
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
     * - When a string, this is considered an icon with classname (.oi).
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

    /**
     * Icon classes for the button this action.
     * - When a string, this is considered as classes for icon
     * - When an object with property `template`, this is an icon class rendered in template.
     *   Template params are provided in `params` and passed to template as a `t-set="templateParams"`
     */
    get iconClass() {
        return typeof this.definition.iconClass === "function"
            ? this.definition.iconClass.call(this, this.params)
            : this.definition.iconClass;
    }

    /** @param {Action} action @returns {boolean|undefined} */
    _isActive(action) {}
    /** States whether this action is currently active. */
    get isActive() {
        if (this.overlayState.isOpen) {
            return true;
        }
        if (this.actions && this.hasPanel) {
            return this.id === this.actions.panelAction?.id;
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
    /**
     * Action to execute when this action is selected
     *
     * @param {Event} ev
     * @param {Object} [param1] @see openPanel
     */
    onSelected(ev, { container, keepPrevious } = {}) {
        if (ev) {
            markEventHandled(ev, "Action.onSelected");
        }
        if (this.hasPanel) {
            if (this.isActive) {
                this.closePanel();
            } else {
                this.openPanel({ container, keepPrevious });
            }
        }
        return (
            this._onSelected(this.params, ev) ??
            this.definition.onSelected?.call(this, this.params, ev)
        );
    }

    /** @param {Action} action @returns {number|undefined} */
    _sequence(action) {}
    _computeSequence() {
        return (
            this._sequence(this.params) ??
            (typeof this.definition.sequence === "function"
                ? this.definition.sequence.call(this, this.params)
                : this.definition.sequence)
        );
    }
    /** Determines the order of this action (smaller first). */
    get sequence() {
        return this._sequenceComputed();
    }

    /** @param {Action} action @returns {ActionGroupId|undefined} */
    _sequenceGroup(action) {}
    _computeSequenceGroup() {
        return (
            this._sequenceGroup(this.params) ??
            (typeof this.definition.sequenceGroup === "function"
                ? this.definition.sequenceGroup.call(this, this.params)
                : this.definition.sequenceGroup)
        );
    }
    get sequenceGroup() {
        return this._sequenceGroupComputed();
    }

    /** @param {Action} action @returns {number|undefined} */
    _sequenceQuick(action) {}
    _computeSequenceQuick() {
        return (
            this._sequenceQuick(this.params) ??
            (typeof this.definition.sequenceQuick === "function"
                ? this.definition.sequenceQuick.call(this, this.params)
                : this.definition.sequenceQuick)
        );
    }
    get sequenceQuick() {
        return this._sequenceQuickComputed();
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
        return toArray(res);
    }

    get tagClassNames() {
        return this.tags.map((tag) => `o-tag-${tag}`).join(" ");
    }

    get closingModeAsDropdown() {
        return this.definition.closingModeAsDropdown ?? "all";
    }
}

/**
 * @template ActionParams_T
 * @template Action_T
 */
export class UseActions {
    /** @type {Action_T} */
    ActionClass = Action;
    /** @type {Component} */
    component;
    /** @type {Readonly<Record<string, any>>} Named ancestors of the component, @see useAncestors */
    ancestors = {};
    /** @type {Map<string, Action_T>} */
    moreActions = new Map();
    /** @type {Map<ActionGroupId, ActionGroupDescription>} */
    actionGroupDescriptions = new Map();
    /** @type {Action<ActionParams_T>[]} */
    transformedActions;
    /** @type {import("models").Store} */
    store;
    /** @type {Action_T[]} Actions whose panel closing the current one goes back to, @see panelAction */
    panelStack = [];
    /** @type {Action_T|null} Action whose panel is shown in the panel of the owner, @see PANEL */
    panelAction = null;

    /**
     * @param {Component} component
     * @param {import("models").Store} store
     * @param {Action_T[]} transformedActions
     */
    constructor(component, store, transformedActions) {
        const self = proxy(this);
        this.component = component;
        this.store = store;
        this.transformedActions = transformedActions;
        // Memoized lists: with per-action memoized condition/sequence these
        // only re-run when the visible set or order actually changes, and
        // otherwise keep a stable array identity so consumers do not
        // re-render for unrelated changes.
        this.actionsComputed = computedShallowEqual(() => self._computeActions());
        this.partitionComputed = computedShallowEqual(() => self._computePartition(), {
            nested: true,
        });
        return self;
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
            moreAction.definition.actionsSignal.set(data.actions);
        } else {
            moreAction = new this.ActionClass({
                ...actionsParams,
                ancestors: this.ancestors,
                owner: this.component,
                id: `more-action:${id}`,
                definition: {
                    ...data,
                    // signal: the dropdown's inner ActionList observes it, and
                    // a reused more-action gets its list swapped in place
                    actionsSignal: signal(data.actions),
                    availableOffline: true,
                    icon: data?.icon ?? "more_vert",
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
        return this.actionsComputed();
    }

    /**
     * @param {string} id
     * @returns {Action_T|undefined} the available action with the given id, @see actions
     */
    get(id) {
        return this.actions.find((action) => action.id === id);
    }

    /** @returns {Panel|undefined} shown in the panel of the owner, @see panelAction */
    get activePanel() {
        return this.panelAction?.condition ? this.panelAction.getPanel() : undefined;
    }

    /** Closes the panel shown in the panel of the owner, and those open in another container. */
    closePanels() {
        for (const action of this.actions) {
            if (action.overlayState.isOpen) {
                action.closePanel();
            }
        }
        this.panelAction?.closePanel();
    }

    _computeActions() {
        const actions = this.transformedActions
            .filter((action) => action.condition)
            .sort((a1, a2) => a1.sequence - a2.sequence);
        return actions;
    }

    /** @return {PartitionedActions<Action_T>} */
    get partition() {
        return this.partitionComputed();
    }

    _computePartition() {
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
        const groupedPanelActions = Object.groupBy(
            actions.filter((a) => a.hasPanel),
            (a) => (a.sequenceQuick ? "quick" : "other")
        );
        groupedPanelActions.quick?.sort((a1, a2) => a1.sequenceQuick - a2.sequenceQuick);
        groupedPanelActions.other?.sort((a1, a2) => a1.sequence - a2.sequence);
        const panelActions = (groupedPanelActions.other ?? []).concat(
            groupedPanelActions.quick ?? []
        );
        return { panelActions, quick, group, other };
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
    actions.ancestors = useAncestors();
    actions.actionGroupDescriptions = new Map(
        actionRegistry
            .getEntries()
            .filter(([id, definition]) => definition?.[IS_ACTION_GROUP_DESCRIPTION_SYM])
            .map(([id, definition]) => [
                Number(id),
                { id: Number(id), ...definition, tags: toArray(definition.tags) },
            ])
    );

    /** @type {Action_T[]} */
    const transformedActions = actionRegistry
        .getEntries()
        .filter(([id, definition]) => definition?.[IS_ACTION_DEFINITION_SYM])
        .map(
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
