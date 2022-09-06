/** @odoo-module **/

// ensure components are registered beforehand.
import '@mail/components/kanban_activity_view/kanban_activity_view';
import { getMessagingComponent } from "@mail/utils/messaging_component";

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const { Component } = owl;

let kanbanActivityViewId = 0;

class KanbanActivityContainer extends Component {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.env.services.messaging.modelManager.messagingCreatedPromise.then(() => {
            if (owl.status(this) === "destroyed") {
                return;
            }
            this.kanbanActivityView = this.env.services.messaging.modelManager.messaging.models['KanbanActivityView'].insert({
                id: kanbanActivityViewId++,
            });
            if (owl.status(this) === "destroyed") {
                // insert might trigger a re-render which might destroy the current component
                this.kanbanActivityView.delete();
                return;
            }
            this.render();
        });
    }
}

Object.assign(KanbanActivityContainer, {
    components: { KanbanActivityView: getMessagingComponent('KanbanActivityView') },
    props: {
        ...standardFieldProps,
    },
    template: 'mail.KanbanActivityContainer',
});

registry.category("fields").add('kanban_activity', KanbanActivityContainer);
