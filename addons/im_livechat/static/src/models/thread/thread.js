odoo.define('im_livechat/static/src/models/thread/thread.js', function (require) {
'use strict';

const {
    registerClassPatchModel,
    registerInstancePatchModel,
} = require('mail/static/src/model/model_core.js');

registerClassPatchModel('mail.thread', 'im_livechat/static/src/models/thread/thread.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('livechat_visitor' in data) {
            if (!data2.members) {
                data2.members = [];
            }
            if (!data.livechat_visitor.id) {
                // Create partner derived from public partner.
                const partner = this.env.models['mail.partner'].create(
                    Object.assign(
                        this.env.models['mail.partner'].convertData(data.livechat_visitor),
                        { id: this.env.models['mail.partner'].getNextPublicId() }
                    )
                );
                data2.correspondent = [['link', partner]];
                data2.members.push(['link', partner]);
            } else {
                const partnerData = this.env.models['mail.partner'].convertData(data.livechat_visitor);
                data2.correspondent = [['insert', partnerData]];
                data2.members.push(['insert', partnerData]);
            }
        }
        return data2;
    },
});

registerInstancePatchModel('mail.thread', 'im_livechat/static/src/models/thread/thread.js', {

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    _computeDisplayName() {
        if (this.channel_type === 'livechat' && this.correspondent) {
            return this.correspondent.nameOrDisplayName;
        }
        return this._super();
    },
});

});
