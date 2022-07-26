/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';

registerModel({
    name: 'ActivityGroup',
    identifyingFields: ['irModel'],
    modelMethods: {
        convertData(data) {
            return {
                actions: data.actions,
                domain: data.domain,
                irModel: insertAndReplace({
                    iconUrl: data.icon,
                    id: data.id,
                    model: data.model,
                    name: data.name,
                }),
                overdue_count: data.overdue_count,
                planned_count: data.planned_count,
                today_count: data.today_count,
                total_count: data.total_count,
                type: data.type,
            };
        },
    },
    recordMethods: {
        /**
         * @private
         */
        _onChangeTotalCount() {
            if (this.type === 'activity' && this.total_count === 0) {
                this.delete();
            }
        },
    },
    fields: {
        actions: attr(),
        activityGroupViews: many('ActivityGroupView', {
            inverse: 'activityGroup',
            isCausal: true,
        }),
        domain: attr(),
        irModel: one('ir.model', {
            inverse: 'activityGroup',
            readonly: true,
            required: true,
        }),
        overdue_count: attr({
            default: 0,
        }),
        planned_count: attr({
            default: 0,
        }),
        today_count: attr({
            default: 0,
        }),
        total_count: attr({
            default: 0,
        }),
        type: attr(),
    },
    onChanges: [
        new OnChange({
            dependencies: ['total_count', 'type'],
            methodName: '_onChangeTotalCount',
        }),
    ],
});
