odoo.define('website_slides.Activity', function (require) {
"use strict";

var Activity = require('mail/static/src/components/activity/activity.js');

Activity.patch("website_slides.Activity", (T)=>
{
    class WebsiteSlidesActivity extends T
    {
        _onGrantAccess(event){
            var partnerId = $(event.currentTarget).data('partner-id');
            this.env.services.rpc({
                model: 'slide.channel',
                method: 'action_grant_access',
                args: [this.activity.res_id, partnerId],
            }).then(this.env.services.reloadPage());
        }

        _onRefuseAccess(event){
            var partnerId = $(event.currentTarget).data('partner-id');
            this.env.services.rpc({
                model: 'slide.channel',
                method: 'action_refuse_access',
                args: [this.activity.res_id, partnerId],
            }).then(this.env.services.reloadPage());
        }

        async willStart(){
            if (this.activity && this.activity.creator && !this.activity.creator.partner){
                    await this.activity.creator.fetchPartner()
                }
            }
    }

    return WebsiteSlidesActivity;
});

Object.assign(Activity,{
    template: 'website_slides.mailActivity'
});

});