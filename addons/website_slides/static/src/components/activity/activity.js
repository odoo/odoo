odoo.define('website_slides/static/src/components/activity/activity.js', function (require) {
'use strict';

const { Activity } = require('@mail/components/activity/activity');

const { patch } = require('web.utils');

const components = { Activity };

patch(components.Activity.prototype, 'website_slides/static/src/components/activity/activity.js', {

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    async _onGrantAccess(ev) {
        await this.env.services.orm.call('slide.channel', 'action_grant_access', [this.activity.thread.id], {
            partner_id: this.activity.requestingPartner.id,
        });
        this.trigger('reload');
    },
    /**
     * @private
     */
    async _onRefuseAccess(ev) {
        await this.env.services.orm.call('slide.channel', 'action_refuse_access', [this.activity.thread.id], {
            partner_id: this.activity.requestingPartner.id
        });
        this.trigger('reload');
    },
});

});
