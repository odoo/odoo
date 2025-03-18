import { localization } from "@web/core/l10n/localization";
import { x2ManyCommands } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { parseXML } from "@web/core/utils/xml";
import { Record } from "@web/model/record";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { FormRenderer } from "@web/views/form/form_renderer";
import { SelectionField } from "@web/views/fields/selection/selection_field";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

import { Component, useState } from "@odoo/owl";


class ResGroupsInformationPopover extends Component {
    static template = "web.ResGroupsInformationPopover";
    static props = {
        close: Function,
        group: Object,
        groups: Object,
        disjoints: Array,
        selectedIds: Array,
        onClose: Function,
    };

    setup() {
        this.group = this.props.group;
        const privilege = this.group.privilege;
        const groups = this.props.groups;

        let implies = this.group.all_implied_ids
            .map((g) => groups[g])
            .filter((g) => this.group.id !== g.id && (!privilege || g.privilege?.id !== privilege.id))
            .sort((a, b) => !a.privilege - !b.privilege);
        implies = implies.filter((g) => !g.privilege || !implies.find((group) => group.privilege?.id === g.privilege?.id && group.level > g.level));

        const others = this.props.selectedIds
            .filter((gId) => this.group.id !== gId && !this.group.all_implied_by_ids.includes(gId))
            .map((gId) => groups[gId].all_implied_ids)
            .flat()
            .map((gId) => groups[gId]);

        this.impliesFromCurrent = implies.filter((g) => !others.includes(g));
        this.implies = implies.filter((g) => others.includes(g));
        this.impliedBy = this.group.all_implied_by_ids
                .map((g) => groups[g])
                .filter((g) => g.id !== this.group.id && this.props.selectedIds.includes(g.id) && (!privilege || g.privilege.id !== privilege.id));

        this.state = useState({
            showGroupWithoutPrivilege: false,
        });
    }

    showExtraGroups () {
        this.state.showGroupWithoutPrivilege = true;
    }

}

class ResUserGroupIdsSelectionField extends SelectionField {
    static template = "web.ResUserGroupIdsSelectionField";

    setup() {
        super.setup();
        this.popover = useService("popover");
        this.groupHierarchy = this.props.record.data.groupHierarchy;
        this.isDebug = odoo.debug;
    }

    get string() {
        const value = this.value;
        return this.options.find((o) => o[0] === value)?.[1] || '';
    }

    get stringImpliedBy() {
        const groups = this.impliedBy.map((g) => (g.privilege ? g.privilege?.name + '/' : '') + g.name);
        return this.implied.name + ' (' + _t("implied by: %s", groups.join(', ')) + ')';
    }

    get selectedIds() {
        return Object.values(this.props.record.data).filter((value) => value && typeof value === 'number');
    }

    get group() {
        return this.groupHierarchy.getGroups()[this.value] || false;
    }

    get implied() {
        const selectedIds = this.selectedIds;
        const groups = this.groupHierarchy.getGroups();
        const implied = this.options.findLast((o) => o[0] && groups[o[0]].all_implied_by_ids.find((gId) => gId !== o[0] && selectedIds.includes(gId)))?.[0] || false;
        return groups[implied];
    }

    get infoGroup () {
        return this.exclusivelyImplied || this.group;
    }

    get exclusivelyImplied () {
        const implied = this.implied;
        const group = this.group;
        if (implied && (!group || implied.level > group.level)) {
            return implied;
        }
        return false;
    }

    get impliedBy() {
        const implied = this.implied;
        if (!implied) {
            return false;
        }
        const selectedIds = this.selectedIds;
        const groups = this.groupHierarchy.getGroups();
        const impliedBy = implied.all_implied_by_ids
                .map((g) => groups[g])
                .filter((g) => g.id !== implied.id && selectedIds.includes(g.id) && (!implied.privilege_id || g.privilege_id !== implied.privilege_id));
        return impliedBy;
    }

    get disjoints() {
        const group = this.implied || this.group;
        if (!group) {
            return false;
        }
        const groups = this.groupHierarchy.getGroups();
        const selectedIds = this.selectedIds;
        const disjoint_ids = group.disjoint_ids
            .map((gId) => group.id === gId ? [] : groups[gId].all_implied_by_ids)
            .flat()
            .filter((gId) => selectedIds.includes(gId));
        if (disjoint_ids.length) {
            return disjoint_ids.map((gId) => groups[gId]);
        }
        return false;
    }

    onClickPlaceholder () {
        if (this.props.options.length === 1) {
            this.onClickSwitch();
        }
    }

    onClickSwitch() {
        const value = this.props.record.data[this.props.name] ? false : this.options[0][0];
        this.props.record.update(
            { [this.props.name]: value },
            { save: this.props.autosave }
        );
    }

    onClickInfoButton(ev) {
        const close = () => {
            this.popoverCloseFn();
            this.popoverCloseFn = null;
        }

        if (this.popoverCloseFn) {
            close();
        }

        this.popoverCloseFn = this.popover.add(
            ev.currentTarget,
            ResGroupsInformationPopover,
            {
                group: this.infoGroup,
                groups: this.groupHierarchy.getGroups(),
                disjoints: this.disjoints || [],
                selectedIds: this.selectedIds,
                onClose: close,
            },
            {
                closeOnClickAway: true,
                position: localization.direction === "rtl" ? "left" : "right",
            },
        );
    }
}

class ResUserGroupIdsSwitchField extends ResUserGroupIdsSelectionField {
    static template = "web.ResUserGroupIdsSwitchField";

    get stringImpliedBy() {
        const groups = this.impliedBy.map((g) => (g.privilege ? g.privilege?.name + '/' : '') + g.name);
        return _t('Yes') + ' (' + _t("implied by: %s", groups.join(', ')) + ')';
    }

}

/**
 * This widget is only used for the 'group_ids' field of the 'res.users' form view,
 * in order to vizualize and configure access rights.
 */
export class ResUserGroupIdsField extends Component {
    static template = "web.ResUserGroupIdsField";
    static components = { Record, FormRenderer };
    static props = { ...standardFieldProps };

    setup() {
        const {groups, sections} = JSON.parse(JSON.stringify(this.props.record.data.view_group_hierarchy));
        this.groupHierarchy = {
            getGroups: () => groups,
            getSections: () => sections,
        };

        for (const section of sections) {
            for (const privilege of section.privileges) {
                for (const gId of privilege.group_ids) {
                    groups[gId].privilege = privilege;
                }
            }
        }

        sections.push({
            id: 'extra',
            name: _t('Extra Rights'),
            privileges: Object.values(groups)
                .filter((group) => !group.privilege_id)
                .map((group) => Object.assign({
                    id: 'group_' + group.id,
                    name: group.name,
                    description: '',
                    group_ids: [group.id],
                })),
        });

        this.fields = {groupHierarchy: {type: "json"}};
        for (const section of sections) {
            for (const privilege of section.privileges) {
                this.fields[this.getFieldName(privilege)] = {
                    type: "selection",
                    string: privilege.name,
                    selection: [[0, ""]].concat(
                                section.id === 'extra' ?
                                [[privilege.group_ids[0], _t('Yes')]] :
                                privilege.group_ids.map((gId) => [gId, groups[gId].name])
                    ),
                    help: privilege.description,
                };
            }
        }

        const models = { main: { fields: this.fields } };
        const arch = `
            <t>
                <group>
                    ${sections.map(
                        (section) => `
                        <group string="${section.name}" ${section.id === 'extra' ? ' colspan="4" col="4" ' + (!odoo.debug ? ' invisible="1" ' : '') : ''}>
                            ${section.privileges.map((cat) => `
                                <field name="${this.getFieldName(cat)}" widget="res_user_group_ids_field_${section.id === 'extra' ? 'switch' : 'selection'}"/>`
                            ).join('')}
                        </group>`
                    ).join('')}
                </group>
            </t>`;
        this.archInfo = new FormArchParser().parse(parseXML(arch), models, "main");
    }

    get values() {
        const values = { groupHierarchy: this.groupHierarchy };
        const ids = this.props.record.data.group_ids.currentIds;
        for (const section of this.groupHierarchy.getSections()) {
            for (const privilege of section.privileges) {
                values[this.getFieldName(privilege)] = privilege.group_ids.find((gId) => ids.includes(gId)) || false;
            }
        }
        return values;
    }

    getFieldName(privilege) {
        return `field_${privilege.id}`;
    }

    onRecordChanged(_, values) {
        const selectedIds = Object.values(values).filter((value) => value && typeof value === 'number');
        return this.props.record.update({ group_ids: [x2ManyCommands.set(selectedIds)] });
    }
}

const resUserGroupIdsSelectionField = {
    component: ResUserGroupIdsSelectionField,
};

const resUserGroupIdsSwithField = {
    component: ResUserGroupIdsSwitchField,
};

export const resUserGroupIdsField = {
    component: ResUserGroupIdsField,
    fieldDependencies: [{ name: "view_group_hierarchy", type: "json", readonly: true }],
};

registry.category("fields").add("res_user_group_ids_field_selection", resUserGroupIdsSelectionField);
registry.category("fields").add("res_user_group_ids_field_switch", resUserGroupIdsSwithField);
registry.category("fields").add("res_user_group_ids", resUserGroupIdsField);
