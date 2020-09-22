odoo.define('website_slides/static/src/models/activity/activity.js', function (require) {
    'use strict';

    const {
        registerClassPatchModel,
        registerFieldPatchModel,
    } = require('mail/static/src/model/model_core.js');

    const { many2one } = require('mail/static/src/model/model_field.js');

    registerClassPatchModel('mail.activity', 'website_slides/static/src/models/activity/activity.js', {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @override
         */
        convertData(data) {
            const data2 = this._super(data);
            if ('request_partner_id' in data) {
                if (!data.request_partner_id) {
                    data2.creatorPartner = [['unlink']];
                } else {
                    data2.creatorPartner = [
                        ['insert', {
                            id: data.request_partner_id[0],
                            display_name: data.request_partner_id[1],
                        }],
                    ];
                }
            }
            return data2;
        },
    });

    registerFieldPatchModel('mail.activity', 'website_slides/static/src/models/activity/activity.js', {
        creatorPartner: many2one('mail.partner'),
    });
});
