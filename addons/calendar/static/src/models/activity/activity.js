/** @odoo-module **/

import {
    registerClassPatchModel,
    registerInstancePatchModel,
    registerFieldPatchModel
} from'@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerFieldPatchModel('mail.activity', 'calendar/static/src/models/activity/activity.js', {
    calendar_event_id: attr({ default: false }),
});

registerClassPatchModel('mail.activity', 'calendar/static/src/models/activity/activity.js', {
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

registerInstancePatchModel('mail.activity', 'calendar/static/src/models/activity/activity.js', {
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
    }
});
