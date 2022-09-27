/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerPatch({
    name: 'Activity',
    modelMethods: {
        /**
         * @override
         */
        convertData(data) {
            const res = this._super(data);
            if ('calendar_event_id' in data) {
                res.calendar_event_id = data.calendar_event_id[0];
            }
            return res;
        },
    },
    recordMethods: {
        /**
         * @override
         */
        async deleteServerRecord() {
            if (!this.calendar_event_id){
                await this._super();
            } else {
                await this.messaging.rpc({
                    model: 'mail.activity',
                    method: 'unlink_w_meeting',
                    args: [[this.id]],
                });
                if (!this.exists()) {
                    return;
                }
                this.delete();
            }
        },
        /**
         * In case the activity is linked to a meeting, we want to open the
         * calendar view instead.
         *
         * @override
         */
        async edit() {
            if (!this.calendar_event_id){
                await this._super();
            } else {
                const action = await this.messaging.rpc({
                    model: 'mail.activity',
                    method: 'action_create_calendar_event',
                    args: [[this.id]],
                });
                this.env.services.action.doAction(action);
            }
        },
    },
    fields: {
        calendar_event_id: attr({
            default: false,
        }),
    },
});
