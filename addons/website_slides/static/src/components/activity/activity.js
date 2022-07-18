/** @odoo-module **/

import { Activity } from '@mail/components/activity/activity';

import { patch } from 'web.utils';

patch(Activity.prototype, 'website_slides/static/src/components/activity/activity.js', {

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    async _onGrantAccess(ev) {
        await this.env.services.rpc({
            model: 'slide.channel',
            method: 'action_grant_access',
            args: [[this.activity.thread.id]],
            kwargs: { partner_id: this.activity.requestingPartner.id },
        });
        if (this.activity) {
            this.activity.delete();
        }
        this.trigger('reload', { keepChanges: true });
    },
    /**
     * @private
     */
    async _onRefuseAccess(ev) {
        await this.env.services.rpc({
            model: 'slide.channel',
            method: 'action_refuse_access',
            args: [[this.activity.thread.id]],
            kwargs: { partner_id: this.activity.requestingPartner.id },
        });
        if (this.activity) {
            this.activity.delete();
        }
        this.trigger('reload', { keepChanges: true });
    },
});
