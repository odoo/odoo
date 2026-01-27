import { registry } from "@web/core/registry";
import { Action, ACTION_TAGS, useAction, UseActions } from "@mail/core/common/action";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { rpc } from "@web/core/network/rpc";

export const channelMemberActionsRegistry = registry.category("discuss.channel.member/actions");

/** @typedef {import("@odoo/owl").Component} Component */
/** @typedef {import("@mail/core/common/action").ActionDefinition} ActionDefinition */
/** @typedef {import("models").ChannelMember} ChannelMember */

/**
 * @typedef {ActionDefinition} ChannelActionDefinition
 */

/**
 * @param {string} id
 * @param {ChannelActionDefinition} definition
 */
export function registerChannelMemberAction(id, definition) {
    channelMemberActionsRegistry.add(id, definition);
}

registerChannelMemberAction("set-admin", {
    condition: ({ member }) => member.canSetAdmin,
    icon: "fa fa-star text-primary",
    name: _t("Set Admin"),
    onSelected: ({ member }) => member.setChannelRole("admin"),
    sequence: 10,
});

registerChannelMemberAction("remove-admin", {
    condition: ({ member }) => member.canRemoveAdmin || member.canRemoveOwner,
    icon: ({ member }) =>
        member.canRemoveOwner ? "fa fa-star-o text-primary" : "fa fa-star-o text-warning",
    name: ({ member }) => (member.canRemoveOwner ? _t("Remove Owner") : _t("Remove Admin")),
    onSelected: ({ member }) => member.setChannelRole(false),
    sequence: 20,
});

registerChannelMemberAction("set-owner", {
    condition: ({ member }) => member.canSetOwner,
    icon: "fa fa-star text-warning",
    name: _t("Set Owner"),
    onSelected: ({ member }) => member.setChannelRole("owner"),
    sequence: 30,
});

registerChannelMemberAction("remove-member", {
    condition: ({ member }) => member.canRemoveMember,
    icon: "fa fa-sign-out",
    name: _t("Remove Member"),
    onSelected: ({ member, store }) => {
        store.env.services.dialog.add(ConfirmationDialog, {
            body: _t('Do you want to remove "%(member_name)s" from this channel?', {
                member_name: member.name,
            }),
            cancel: () => {},
            confirm: () => {
                rpc("/discuss/channel/remove_member", {
                    member_id: member.id,
                });
            },
        });
    },
    sequence: 40,
    tags: [ACTION_TAGS.DANGER],
});

export class ChannelMemberAction extends Action {
    /** @type {() => ChannelMember} */
    memberFn;

    /**
     * @param {Object} param0
     * @param {Thread|() => ChannelMember} member
     */
    constructor({ member }) {
        super(...arguments);
        this.memberFn = typeof member === "function" ? member : () => member;
    }

    get params() {
        return Object.assign(super.params, { member: this.memberFn() });
    }
}

class UseChannelMemberActions extends UseActions {
    ActionClass = ChannelMemberAction;
}

/**
 * @param {Object} [params0={}]
 * @param {ChannelMember|() => ChannelMember} member
 */
export function useChannelMemberActions({ member } = {}) {
    return useAction(channelMemberActionsRegistry, UseChannelMemberActions, ChannelMemberAction, {
        member,
    });
}
