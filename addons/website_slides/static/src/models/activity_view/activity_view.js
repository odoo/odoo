/** @odoo-module **/

import { addRecordMethods, patchLifecycleHooks } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/activity_view/activity_view';

patchLifecycleHooks('ActivityView', {
    _created() {
        this._super();
        this.onGrantAccess = this.onGrantAccess.bind(this);
        this.onRefuseAccess = this.onRefuseAccess.bind(this);
    },
});

addRecordMethods('ActivityView', {
    /**
     * Handles click on the "grant access" button.
     */
    async onGrantAccess(ev) {
        const { chatter } = this.activityBoxView; // save value before deleting activity
        await this.env.services.rpc({
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
        await this.env.services.rpc({
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
});
