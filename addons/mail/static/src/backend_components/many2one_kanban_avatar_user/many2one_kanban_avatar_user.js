/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const { Component } = owl;

export class Many2oneKanbanAvatarUser extends Component {

    get url() {
        return `/web/image/${this.props.relation}/${this.props.value[0]}/avatar_128`;
    }

    async openChat(ev) {
        ev.stopPropagation();
        const messaging = await Component.env.services.messaging.get();
        messaging.openChat({ userId: this.props.value[0] });
    }
}

Many2oneKanbanAvatarUser.supportedTypes = ['many2one'];
Many2oneKanbanAvatarUser.props = {
    ...standardFieldProps,
    relation: { type: String, optional: true },
};
Many2oneKanbanAvatarUser.template = 'mail.Many2OneKanbanAvatarUser';
Many2oneKanbanAvatarUser.extractProps = ({ attrs, field }) => {
    return {
        relation: field.relation,
    };
};

registry.category('fields').add('kanban.many2one_avatar_user', Many2oneKanbanAvatarUser);
registry.category('fields').add('activity.many2one_avatar_user', Many2oneKanbanAvatarUser);
