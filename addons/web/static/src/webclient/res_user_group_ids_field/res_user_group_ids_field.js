import { x2ManyCommands } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { parseXML } from "@web/core/utils/xml";
import { Record } from "@web/model/record";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { FormRenderer } from "@web/views/form/form_renderer";

import { Component } from "@odoo/owl";

/**
 * This widget is only used for the 'group_ids' field of the 'res.users' form view,
 * in order to vizualize and configure access rights.
 */
export class ResUserGroupIdsField extends Component {
    static template = "web.ResUserGroupIdsField";
    static components = { Record, FormRenderer };
    static props = { ...standardFieldProps };

    setup() {
        this.sections = this.props.record.data.view_group_hierarchy;
        this.categories = this.sections.map((section) => section.categories).flat();
        this.groupIdsInCategories = Object.values(this.categories)
            .map((c) => c.groups.map((g) => g[0]))
            .flat();

        this.fields = {};
        for (const category of this.categories) {
            this.fields[this.getFieldName(category)] = {
                type: "selection",
                string: category.name,
                selection: [[false, ""]].concat(category.groups),
                help: category.description,
            };
        }
        const models = { main: { fields: this.fields } };
        const arch = `
            <t>
                <group>
                    ${this.sections.map(
                        (section) => `
                        <group string="${section.name}">
                            ${section.categories.map((cat) => `<field name="field_${cat.id}"/>`)}
                        </group>`
                    )}
                </group>
            </t>`;
        this.archInfo = new FormArchParser().parse(parseXML(arch), models, "main");
        this.hooks = {
            onRecordChanged: this.onRecordChanged.bind(this),
        };
    }

    get values() {
        const values = {};
        const ids = this.props.record.data.group_ids.currentIds;
        for (const category of this.categories) {
            values[this.getFieldName(category)] =
                category.groups.find((g) => ids.includes(g[0]))?.[0] || false;
        }
        return values;
    }

    getFieldName(category) {
        return `field_${category.id}`;
    }

    onRecordChanged(_, values) {
        const groupIds = Object.values(values).filter((groupId) => groupId);
        const groupIdsNotInCategories = this.props.record.data.group_ids.currentIds.filter(
            (id) => !this.groupIdsInCategories.includes(id)
        );
        const allGroupIds = groupIdsNotInCategories.concat(groupIds);
        return this.props.record.update({ group_ids: [x2ManyCommands.set(allGroupIds)] });
    }
}

export const resUserGroupIdsField = {
    component: ResUserGroupIdsField,
    fieldDependencies: [{ name: "view_group_hierarchy", type: "json", readonly: true }],
};

registry.category("fields").add("res_user_group_ids", resUserGroupIdsField);
