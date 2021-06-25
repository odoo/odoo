/** @odoo-module **/

import DiscussWidget from '@mail/widgets/discuss/discuss';

DiscussWidget.include({
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
