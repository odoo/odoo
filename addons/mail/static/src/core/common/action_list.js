import { attClassObjectToString } from "@mail/utils/common/format";
import { propSignal } from "@mail/utils/common/hooks";
import { Component, computed, onWillUnmount, shallowEqual, t, useProps, xml } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Action as ActionModel, ACTION_TAGS } from "@mail/core/common/action";
import { useService } from "@web/core/utils/hooks";

/**
 * Params of an action, like in its definition, along with where it is rendered. `parentAction` is
 * the more-action whose dropdown lists the action, if any.
 *
 * @typedef {import("@mail/core/common/action").ActionParams<ActionModel, import("@mail/core/common/action").UseActions> & { dropdown: boolean, inline: boolean, parentAction?: ActionModel }} ActionComponentParams
 */

/**
 * Picks the component of an action, @see BaseAction. Returning nothing falls back to the default.
 *
 * @typedef {(params: ActionComponentParams) => typeof BaseAction | undefined} GetActionComponent
 */

/**
 * Component of the actions of an ActionList, @see BaseAction: either one component for all the
 * actions of the list, or a function picking it per action. Only the function is passed on to the
 * dropdown of a more-action, as a component of the list's own actions does not suit its items.
 *
 * @typedef {typeof BaseAction | GetActionComponent} ActionComponent
 */

/** @param {ActionComponent} [actionComponent] */
function isComponent(actionComponent) {
    return actionComponent?.prototype instanceof Component;
}

/** Props of an ActionList passed on to its actions; inline or dropdown is given by their component. */
const actionListProps = ["actionComponent?", "fw?", "hasBtnBg?"];

const actionListPropsSchema = {
    /** @see ActionComponent */
    actionComponent: t
        .or([t.component(), t.function([t.object()], t.component().optional())])
        .optional(),
    fw: t.boolean().optional(true),
    hasBtnBg: t.boolean().optional(),
};

/**
 * Renders one action of an ActionList; extend it to change how actions look in a given place.
 *
 * @see InlineAction and @see DropdownAction are used by default. The look of an action depends on
 * where it is shown, so the place that mounts an ActionList passes an extension of them
 * (`actionComponent` prop) when it needs UI tweaks, rather than tweaking the action definition or
 * relying on an environment flag. The classes of the button are gathered in `classObj`, which an
 * extension extends with its own concerns, e.g.
 * `get classObj() { return { ...super.classObj, ...this.paddingClass }; }`, or overrides just the
 * concern it tweaks, e.g. `get paddingClass() { return { ...super.paddingClass, "px-3": true }; }`.
 */
export class BaseAction extends Component {
    static template = xml`<div/>`;

    get ActionList() {
        return ActionList;
    }

    get Dropdown() {
        return Dropdown;
    }

    setup() {
        super.setup();
        this.props = useProps({
            action: t.instanceOf(ActionModel),
            isFirstInGroup: t.boolean().optional(),
            isLastInGroup: t.boolean().optional(),
            style: t.string().optional(),
            ...actionListPropsSchema,
        });
        this.store = useService("mail.store");
        this.ui = useService("ui");
        if (this.props.action.definition?.isMoreAction) {
            onWillUnmount(() => {
                this.props.action.dropdownState.close();
            });
        }
    }

    get action() {
        return this.props.action;
    }

    /** @see ActionComponent, a component of this list's own actions is not passed on. */
    get dropdownActionComponent() {
        return isComponent(this.props.actionComponent) ? undefined : this.props.actionComponent;
    }

    get attrs() {
        return {
            "aria-label": this.action.name,
            disabled: this.action.disabledCondition,
            name: this.action.id,
            "data-sequence": this.action.sequence,
            "data-sequence-group": this.action.sequenceGroup,
            "data-sequence-quick": this.action.sequenceQuick,
            ...this.action.btnAttrs,
        };
    }

    get btnClass() {
        return attClassObjectToString(this.classObj);
    }

    /** Classes of the button, @see BaseAction on how to extend them. */
    get classObj() {
        return {
            ...this.coreClass,
            ...this.colorClass,
            ...this.themeClass,
            ...this.dynamicClass,
        };
    }

    get coreClass() {
        return {
            "o-mail-ActionList-button btn position-relative": true,
            "o-first": this.props.isFirstInGroup,
            "o-last": this.props.isLastInGroup,
            active: this.action.isActive,
            "o-hasBtnBg": this.hasBtnBg,
        };
    }

    get colorClass() {
        const tags = this.action.tags;
        return {
            "btn-secondary":
                !tags.includes(ACTION_TAGS.PRIMARY) &&
                !tags.includes(ACTION_TAGS.DANGER) &&
                !tags.includes(ACTION_TAGS.SUCCESS),
            "btn-primary": tags.includes(ACTION_TAGS.PRIMARY),
            "btn-danger": tags.includes(ACTION_TAGS.DANGER),
            "btn-success": tags.includes(ACTION_TAGS.SUCCESS),
        };
    }

    get themeClass() {
        return { "o-discussCallTheme": this.env.inDiscussCallTheme };
    }

    get dynamicClass() {
        return { [this.action.tagClassNames]: true };
    }

    get hasBtnBg() {
        return this.props.hasBtnBg || this.props.action.hasBtnBg;
    }

    /** Whether the component of the action definition replaces the button of the action. */
    get hasDefinitionComponent() {
        return Boolean(this.action.component && this.action.componentCondition);
    }

    get iconClass() {
        return { "oi-fw": this.props.fw };
    }

    get label() {
        return this.action.name;
    }

    get labelClass() {
        return {};
    }

    get showLabel() {
        return Boolean(this.action.name);
    }

    onSelected(action, ev) {
        action.onSelected?.(ev);
    }
}

/**
 * Default component of an action in an inline ActionList, i.e. a button, joined into the rounded
 * shape of its group.
 */
export class InlineAction extends BaseAction {
    static template = "mail.InlineAction";

    get classObj() {
        return {
            ...super.classObj,
            ...this.borderClass,
            ...this.roundnessClass,
            ...this.marginClass,
            ...this.paddingClass,
        };
    }

    get coreClass() {
        return { ...super.coreClass, "btn-group-item o-inline": true };
    }

    get borderClass() {
        return {
            "border-0": !this.hasBtnBg && this.action.icon,
            "border-2": !this.hasBtnBg && !this.action.icon,
        };
    }

    get roundnessClass() {
        return {
            "rounded-start-3": this.props.isFirstInGroup,
            "rounded-end-3": this.props.isLastInGroup,
        };
    }

    get marginClass() {
        return { "o-mx-0_5": !this.hasBtnBg && !this.action.icon };
    }

    get paddingClass() {
        return { "o-px-0_5": !this.hasBtnBg && !this.action.icon };
    }

    get attrs() {
        return { ...super.attrs, title: this.action.name };
    }

    /** A button with an icon shows only its icon, its name being its title. */
    get showLabel() {
        return Boolean(super.showLabel && !this.action.icon);
    }
}

/** Inline action whose button is a circle when it has an icon, e.g. in the composer and in messages. */
export class CircleInlineAction extends InlineAction {
    get isCircle() {
        return Boolean(this.action.icon);
    }

    get classObj() {
        return { ...super.classObj, "o_btn_circle d-flex align-items-center": this.isCircle };
    }

    get roundnessClass() {
        if (!this.isCircle) {
            return super.roundnessClass;
        }
        return { "rounded-circle": true };
    }
}

/** Default component of an action in a dropdown ActionList, i.e. a dropdown item. */
export class DropdownAction extends BaseAction {
    static components = { DropdownItem };
    static template = "mail.DropdownAction";

    get classObj() {
        return { ...super.classObj, ...this.alignmentClass, ...this.paddingClass };
    }

    get alignmentClass() {
        return {
            "d-flex align-items-center dropdown-item_active_noarrow": true,
            "gap-2": this.ui.isSmall,
            "text-start gap-1": !this.ui.isSmall,
        };
    }

    get paddingClass() {
        return {
            "px-3 py-2": this.ui.isSmall,
            "px-2 py-1": !this.ui.isSmall,
        };
    }

    get iconClass() {
        return { ...super.iconClass, "o-fs-small": true };
    }

    get labelClass() {
        return { ...super.labelClass, "mx-1": true };
    }
}

export class ActionList extends Component {
    static template = "mail.ActionList";

    /**
     * @param {ActionModel} action
     * @returns {typeof BaseAction}
     */
    getActionComponent(action) {
        if (isComponent(this.props.actionComponent)) {
            return this.props.actionComponent;
        }
        /** @type {ActionComponentParams} */
        const params = {
            ...action.params,
            dropdown: Boolean(this.props.dropdown),
            inline: Boolean(this.props.inline),
            parentAction: this.props.parentAction,
        };
        return (
            this.props.actionComponent?.(params) ??
            (this.props.dropdown ? DropdownAction : InlineAction)
        );
    }

    getActionProps(action, group, { index, isFirstInGroup, isLastInGroup } = {}) {
        return {
            action,
            group,
            isFirstInGroup,
            isLastInGroup,
            ...Object.fromEntries(
                actionListProps.map((propName) => {
                    const actualPropName = propName.endsWith("?")
                        ? propName.substring(0, propName.length - 1)
                        : propName;
                    return [actualPropName, this.props[actualPropName]];
                })
            ),
            style: `z-index: ${group.length - index + (action.hotkey ? 1 : 0)}`,
        };
    }

    setup() {
        super.setup();
        this.actions = propSignal(
            "actions",
            t.array(t.or([t.instanceOf(ActionModel), t.array(t.instanceOf(ActionModel))]))
        );
        this.props = useProps({
            dropdown: t.boolean().optional(),
            groupClass: t.string().optional(),
            inline: t.boolean().optional(),
            /** More-action whose dropdown shows this list. */
            parentAction: t.instanceOf(ActionModel).optional(),
            ...actionListPropsSchema,
        });
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.actionListProps = actionListProps;
    }

    groups = computed(
        () => {
            const actions = this.actions();
            let groups;
            if (actions.find((i) => Array.isArray(i))) {
                groups = actions;
            } else {
                groups = [actions];
            }
            return groups.filter((group) => group.length); // don't show empty groups
        },
        { equals: shallowEqual }
    );
}
