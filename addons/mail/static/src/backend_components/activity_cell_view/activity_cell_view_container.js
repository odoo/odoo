/** @odoo-module **/

import { useMessagingContainer } from "@mail/component_hooks/use_messaging_container";
import { insert } from "@mail/model";

import { Component, onWillDestroy, onWillUpdateProps } from "@odoo/owl";

const getNextId = (function () {
    let tmpId = 0;
    return () => {
        tmpId += 1;
        return tmpId;
    };
})();

/**
 * Container for messaging component ActivityCellView ensuring messaging
 * records are ready before rendering ActivityCellView component.
 */
export class ActivityCellViewContainer extends Component {
    /**
     * @override
     */
    setup() {
        useMessagingContainer();
        super.setup();
        this.activityCellView = undefined;
        this.activityCellViewId = getNextId();
        this._insertFromProps(this.props);
        onWillUpdateProps((nextProps) => this._insertFromProps(nextProps));
        onWillDestroy(() => this._deleteRecord());
    }

    /**
     * @private
     */
    _deleteRecord() {
        if (this.activityCellView) {
            if (this.activityCellView.exists()) {
                this.activityCellView.delete();
            }
            this.activityCellView = undefined;
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
        const activityCellView = messaging.models["ActivityCellView"].insert({
            activityType: {
                id: props.activityTypeId,
            },
            closestDeadline: props.closestDeadline,
            id: this.activityCellViewId,
            reloadFunc: props.reloadFunc,
            thread: {
                activities: insert(
                    props.activityIds.map((activityId) => {
                        return {
                            id: activityId,
                            type: {
                                id: props.activityTypeId,
                            },
                        };
                    })
                ),
                hasActivities: true,
                id: props.resId,
                model: props.resModel,
            },
        });
        if (activityCellView !== this.activityCellView) {
            this._deleteRecord();
            this.activityCellView = activityCellView;
        }
        this.render();
    }
}

Object.assign(ActivityCellViewContainer, {
    props: {
        activityIds: {
            type: Array,
            elements: Number,
        },
        activityTypeId: Number,
        closestDeadline: String,
        reloadFunc: Function,
        resId: Number,
        resModel: String,
    },
    template: "mail.ActivityCellViewContainer",
});
