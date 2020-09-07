odoo.define('im_livechat/static/src/models/partner/partner.js', function (require) {
'use strict';

const {
    registerClassPatchModel,
} = require('mail/static/src/model/model_core.js');

let nextPublicId = -1;

registerClassPatchModel('mail.partner', 'im_livechat/static/src/models/partner/partner.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    getNextPublicId() {
        const id = nextPublicId;
        nextPublicId -= 1;
        return id;
    },
});

});
