/** @odoo-module **/

import { addFields, patchModelMethods, patchRecordMethods } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/activity';

addFields('Activity', {
    calendar_event_id: attr({ default: false }),
});

patchModelMethods('Activity', {
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
});

patchRecordMethods('Activity', {
    /**
     * @override
     */
    async deleteServerRecord() {
        if (!this.calendar_event_id){
            await this._super();
        } else {
            await this.async(() => this.env.services.rpc({
                model: 'mail.activity',
                method: 'unlink_w_meeting',
                args: [[this.id]],
            }));
            this.delete();
        }
    },
    /**
     * In case the activity is linked to a meeting, we want to open the calendar view instead.
     *
     * @override
     */
    async edit() {
        if (!this.calendar_event_id){
            await this._super();
        } else {
            const action = await this.async(() => this.env.services.rpc({
                model: 'mail.activity',
                method: 'action_create_calendar_event',
                args: [[this.id]],
            }));
            this.env.bus.trigger('do-action', {
                action
            });
        }
    },
});
