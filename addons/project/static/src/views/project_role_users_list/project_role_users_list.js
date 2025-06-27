import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Many2ManyTagsAvatarUserField } from "@mail/views/web/fields/many2many_avatar_user_field/many2many_avatar_user_field";

export class ProjectRoleUsersList extends Component {
    static template = "ProjectRoleUsersList";
    static props = standardFieldProps;
    static components = { Many2ManyTagsAvatarUserField };
}

registry.category("fields").add("project_role_users_list", {
    component: ProjectRoleUsersList,
});
