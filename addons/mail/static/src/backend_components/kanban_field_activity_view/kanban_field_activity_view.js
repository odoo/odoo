/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class KanbanFieldActivityView extends Component {

    get kanbanFieldActivityView() {
        return this.props.record;
    }

}

Object.assign(KanbanFieldActivityView, {
    props: { record: Object },
    template: 'mail.KanbanFieldActivityView',
});

registerMessagingComponent(KanbanFieldActivityView);
