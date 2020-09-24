odoo.define('im_livechat/static/src/widgets/discuss/discuss.js', function (require) {
'use strict';

const Discuss = require('mail/static/src/widgets/discuss/discuss.js');

Discuss.include({
    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    _shouldHaveInviteButton() {
        if (
            this.discuss.thread &&
            this.discuss.thread.channel_type === 'livechat'
        ) {
            return true;
        }
        return this._super();
    },
});

});
