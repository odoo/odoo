import { Component, useState, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Field } from "@web/views/fields/field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import {
    Many2ManyTagsAvatarUserField,
} from "@mail/views/web/fields/many2many_avatar_user_field/many2many_avatar_user_field";
export class ProjectRoleLoadMoreWidget extends Component {
    static template = "ProjectRoleLoadMoreWidget";
    static props = {
        ...standardFieldProps,
    };
    static components = {
        Many2ManyTagsAvatarUserField,
        Field,
    };
    setup() {
        this.state = useState({
            allRoleItems: this.props.record.data.role_to_users_ids.records,
        });

        useEffect(
            () => {
                this.loadInitialData();
            },
            () => this.getLoadTemplatesDeps()
        );
    }

    getLoadTemplatesDeps() {
        return [this?.props?.record?.data?.role_to_users_ids?.records];
    }

    loadInitialData() {
        const allData = this.props.record.data.role_to_users_ids.records;
        this.state.allRoleItems = [...allData];
    }

}

registry.category("fields").add("project_role_load_more", {
    component: ProjectRoleLoadMoreWidget,
});
