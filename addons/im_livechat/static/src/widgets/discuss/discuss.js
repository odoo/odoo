/** @odoo-module **/

import Discuss from '@mail/widgets/discuss/discuss';

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
