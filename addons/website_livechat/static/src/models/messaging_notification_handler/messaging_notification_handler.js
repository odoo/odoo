/** @odoo-module **/

export const instancePatchMessagingNoficationHandler = {

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    _handleNotificationPartner(data) {
        const { info } = data;
        if (info === 'send_chat_request') {
            this._handleNotificationPartnerChannel(data);
            const channel = this.env.models['mail.thread'].findFromIdentifyingData({
                id: data.id,
                model: 'mail.channel',
            });
            this.env.messaging.chatWindowManager.openThread(channel, {
                makeActive: true,
            });
            return;
        }
        return this._super(data);
    },
};
