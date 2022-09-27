/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'ActivityView',
    recordMethods: {
        /**
         * Handles click on the "grant access" button.
         */
        async onGrantAccess(ev) {
            const { chatter } = this.activityBoxView; // save value before deleting activity
            await this.messaging.rpc({
                model: 'slide.channel',
                method: 'action_grant_access',
                args: [[this.activity.thread.id]],
                kwargs: { partner_id: this.activity.requestingPartner.id },
            });
            if (this.activity) {
                this.activity.delete();
            }
            chatter.reloadParentView();
        },
        /**
         * Handles click on the "refuse access" button.
         */
        async onRefuseAccess(ev) {
            const { chatter } = this.activityBoxView; // save value before deleting activity
            await this.messaging.rpc({
                model: 'slide.channel',
                method: 'action_refuse_access',
                args: [[this.activity.thread.id]],
                kwargs: { partner_id: this.activity.requestingPartner.id },
            });
            if (this.activity) {
                this.activity.delete();
            }
            chatter.reloadParentView();
        },
    },
});
