/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class KanbanActivityView extends Component {}

Object.assign(KanbanActivityView, {
    props: { record: Object },
    template: 'mail.KanbanActivityView',
});

registerMessagingComponent(KanbanActivityView);
