/** @odoo-module */

import { Component } from "@odoo/owl";
import { Layout } from "@web/search/layout";
import { standardViewProps } from "@web/views/standard_view_props";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { sprintf } from "@web/core/utils/strings";
import { useModel } from "@web/views/model";
import { useService } from "@web/core/utils/hooks";

export class ActivityController extends Component {
    static components = { Layout };
    static props = {
        ...standardViewProps,
        Model: Function,
        Renderer: Function,
        archInfo: Object,
    };
    static template = "mail.ActivityController";

    setup() {
        const { rootState } = this.props.state || {};
        this.model = useModel(
            this.props.Model,
            {
                activeFields: this.props.archInfo.activeFields,
                resModel: this.props.resModel,
                fields: this.props.fields,
                viewMode: "activity",
                rootState,
            },
            { ignoreUseSampleModel: true }
        );

        this.dialog = useService("dialog");
        this.action = useService("action");
        this.messaging = useService("messaging");
    }

    scheduleActivity() {
        this.dialog.add(SelectCreateDialog, {
            resModel: this.props.resModel,
            searchViewId: this.env.searchModel.searchViewId,
            domain: this.model.originalDomain,
            title: sprintf(this.env._t("Search: %s"), this.props.archInfo.title),
            multiSelect: false,
            context: this.props.context,
            onSelected: async (resIds) => {
                const messaging = await this.messaging.get();
                const thread = messaging.models["Thread"].insert({
                    id: resIds[0],
                    model: this.props.resModel,
                });
                await messaging.openActivityForm({ thread });
                this.model.load({ domain: this.model.originalDomain });
            },
        });
    }

    openActivityFormView(resId, activityTypeId) {
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "mail.activity",
                views: [[false, "form"]],
                view_mode: "form",
                view_type: "form",
                res_id: false,
                target: "new",
                context: {
                    default_res_id: resId,
                    default_res_model: this.props.resModel,
                    default_activity_type_id: activityTypeId,
                },
            },
            {
                onClose: () => this.model.load({ domain: this.model.originalDomain }),
            }
        );
    }

    sendMailTemplate(templateID, activityTypeID) {
        const groupedActivities = this.model.activityData.grouped_activities;
        const resIds = [];
        for (const resId in groupedActivities) {
            const activityByType = groupedActivities[resId];
            const activity = activityByType[activityTypeID];
            if (activity) {
                resIds.push(parseInt(resId));
            }
        }
        this.model.orm.call(this.props.resModel, "activity_send_mail", [resIds, templateID], {});
    }

    async openRecord(record, mode) {
        const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
        this.props.selectRecord(record.resId, { activeIds, mode });
    }

    get rendererProps() {
        return {
            activityTypes: this.model.activityData.activity_types,
            activityResIds: this.model.activityData.activity_res_ids,
            fields: this.model.root.fields,
            records: this.model.root.records,
            resModel: this.props.resModel,
            archInfo: this.props.archInfo,
            groupedActivities: this.model.activityData.grouped_activities,
            scheduleActivity: this.scheduleActivity.bind(this),
            onReloadData: () => this.model.load({ domain: this.model.originalDomain }),
            onEmptyCell: this.openActivityFormView.bind(this),
            onSendMailTemplate: this.sendMailTemplate.bind(this),
            openRecord: this.openRecord.bind(this),
        };
    }
}
