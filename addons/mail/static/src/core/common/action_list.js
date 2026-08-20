import { Action as ActionModel } from "@mail/core/common/action";
import {
    ActionButton,
    actionButtonProps,
    actionButtonPropsSchema,
} from "@mail/core/common/action_button";
import { CallSurfaceActionButton } from "@mail/core/common/call_surface_action_button";
import { ComposerActionButton } from "@mail/core/common/composer_action_button";
import { MessageActionButton } from "@mail/core/common/message_action_button";
import { propSignal } from "@mail/utils/common/hooks";
import { Component, computed, onWillUnmount, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useService } from "@web/core/utils/hooks";

const actionListProps = actionButtonProps;
const actionListPropsSchema = actionButtonPropsSchema;

/**
 * Wraps an action's chrome with its optional own dropdown (e.g. a "more actions"
 * overflow menu), and picks which {@link ActionButton} variant renders that chrome
 * based on the ambient context: the composer toolbar, a message's hover toolbar, a
 * call surface (call view, meeting, call invitation, pip banner, welcome page), or
 * the default/generic case.
 */
class Action extends Component {
    static template = "mail.Action";

    get ActionList() {
        return ActionList;
    }

    get Dropdown() {
        return Dropdown;
    }

    /** Which {@link ActionButton} variant should render this action's chrome. */
    get ButtonComponent() {
        if (this.env.inComposer) {
            return ComposerActionButton;
        }
        if (this.env.inMessage) {
            return MessageActionButton;
        }
        if (this.isCallSurface) {
            return CallSurfaceActionButton;
        }
        return ActionButton;
    }

    /** Whether this action renders on a call surface (see {@link CallSurfaceActionButton}). */
    get isCallSurface() {
        return (
            (this.env?.inDiscussCallView ||
                this.env?.inCallInvitation ||
                this.env.isDiscussPipBanner ||
                this.env?.inWelcomePage) &&
            !this.env.inDiscussActionPanel
        );
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
        if (this.props.action.definition?.isMoreAction) {
            onWillUnmount(() => {
                this.props.action.dropdownState.close();
            });
        }
    }

    get action() {
        return this.props.action;
    }
}

export class ActionList extends Component {
    static components = { Action };
    static template = "mail.ActionList";

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
            groupClass: t.string().optional(),
            ...actionListPropsSchema,
        });
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.actionListProps = actionListProps;
    }

    groups = computed(() => {
        const actions = this.actions();
        let groups;
        if (actions.find((i) => Array.isArray(i))) {
            groups = actions;
        } else {
            groups = [actions];
        }
        return groups.filter((group) => group.length); // don't show empty groups
    });

    get hasBtnBg() {
        return this.props.odooControlPanelSwitchStyle || this.props.hasBtnBg;
    }
}
