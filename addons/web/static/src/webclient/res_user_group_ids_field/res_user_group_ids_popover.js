import { Component, useState } from "@odoo/owl";
import { groupBy } from "@web/core/utils/arrays";
import { useService } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/objects";

export class ResUserGroupIdsPopover extends Component {
    static template = "web.ResUserGroupIdsPopover";
    static props = {
        close: Function,
        groupId: [Number, Boolean],
        groups: Object,
        privileges: Object,
    };

    setup() {
        this.actionService = useService("action");

        this.state = useState({
            showExtraGroups: false,
        });

        this.groups = this.props.groups;
        this.privileges = this.props.privileges;
        this.group = this.groups[this.props.groupId];
        this.privilege = this.privileges[this.group.privilege_id];

        // filter out impliedBy groups from same privilege
        this.impliedGroups = this.group.impliedByIds
            .map((gid) => this.groups[gid])
            .filter((g) => !this.privilege || g.privilege_id !== this.privilege.id);

        // split joint/joint extra/exclusive implies (at most one group by privilege, the one with
        // higher level, and omit groups of same privilege as the current group)
        const implyGroups = this.group.implyIds.map((gid) => this.groups[gid]);
        const implyGroupsByPrivilege = groupBy(implyGroups, (g) => g.privilege_id);
        const keysToOmit = this.privilege ? ["false", String(this.privilege.id)] : ["false"];
        const groupsFromOtherPrivileges = omit(implyGroupsByPrivilege, ...keysToOmit);
        const higherLevelGroups = Object.values(groupsFromOtherPrivileges).map((groups) => groups[groups.length-1]);
        const groupsWithoutPrivilege = implyGroupsByPrivilege[false] || [];
        const implyGroupsToDisplay = groupsWithoutPrivilege.concat(higherLevelGroups);
        const { exclusive, joint, extra } = groupBy(implyGroupsToDisplay, (g) => {
            if (g.impliedByIds.length > 1) {
                return g.privilege_id ? "joint" : "extra";
            }
            return "exclusive";
        });
        this.exclusiveImplyGroups = exclusive || [];
        this.jointImplyGroups = joint || [];
        this.jointExtraImplyGroups = extra || [];
    }

    getGroupDisplayName(group) {
        const prefix = group.privilege_id ? `${this.privileges[group.privilege_id].name}/` : "";
        return `${prefix}${group.name}`;
    }

    onGroupClicked(group) {
        this.actionService.doAction({
            res_id: group.id,
            res_model: "res.groups",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        });
    }
}
