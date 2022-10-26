/** @odoo-module **/

// ensure components are registered beforehand.
import '@mail/backend_components/kanban_field_activity_view/kanban_field_activity_view';
import { getMessagingComponent } from '@mail/utils/messaging_component';

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const { Component, onWillDestroy, onWillUpdateProps } = owl;

const getNextId = (function () {
    let tmpId = 0;
    return () => {
        tmpId += 1;
        return tmpId;
    };
})();

/**
 * Container for messaging component KanbanFieldActivityView ensuring messaging
 * records are ready before rendering KanbanFieldActivityView component.
 */
export class KanbanFieldActivityViewContainer extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this.kanbanFieldActivityView = undefined;
        this.kanbanFieldActivityViewId = getNextId();
        this._insertFromProps(this.props);
        onWillUpdateProps(nextProps => this._insertFromProps(nextProps));
        onWillDestroy(() => this._deleteRecord());
    }

    /**
     * @private
     */
    _deleteRecord() {
        if (this.kanbanFieldActivityView) {
            if (this.kanbanFieldActivityView.exists()) {
                this.kanbanFieldActivityView.delete();
            }
            this.kanbanFieldActivityView = undefined;
        }
    }

    /**
     * @private
     */
    async _insertFromProps(props) {
        const messaging = await this.env.services.messaging.get();
        if (owl.status(this) === "destroyed") {
            this._deleteRecord();
            return;
        }
        const kanbanFieldActivityView = messaging.models['KanbanFieldActivityView'].insert({
            id: this.kanbanFieldActivityViewId,
            thread: {
                activities: this.props.value.records.map(activityData => {
                    return {
                        id: activityData.resId,
                    };
                }),
                hasActivities: true,
                id: props.record.resId,
                model: props.record.resModel,
            },
            webRecord: props.record,
        });
        if (kanbanFieldActivityView !== this.kanbanFieldActivityView) {
            this._deleteRecord();
            this.kanbanFieldActivityView = kanbanFieldActivityView;
        }
        this.render();
    }

}

Object.assign(KanbanFieldActivityViewContainer, {
    components: { KanbanFieldActivityView: getMessagingComponent('KanbanFieldActivityView') },
    fieldDependencies: {
        activity_exception_decoration: { type: 'selection' },
        activity_exception_icon: { type: 'char' },
        activity_state: { type: 'selection' },
        activity_summary: { type: 'char' },
        activity_type_icon: { type: 'char' },
        activity_type_id: { type: 'many2one', relation: 'mail.activity.type' },
    },
    props: {
        ...standardFieldProps,
    },
    template: 'mail.KanbanFieldActivityViewContainer',
});

registry.category('fields').add('kanban_activity', KanbanFieldActivityViewContainer);
