odoo.define('mail_media_repository/static/src/models/composer/composer.js', function (require) {
'use strict';

const {
    registerInstancePatchModel,
} = require('mail/static/src/model/model_core.js');

registerInstancePatchModel('mail.composer', 'mail_media_repository/static/src/models/composer/composer.js', {

    /**
     * @override
     */
    async postMessageWithMedia(media) {
        const thread = this.thread;
        this.thread.unregisterCurrentPartnerIsTyping({ immediateNotify: true });
        const body = "";
        let postData = {
            attachment_ids: [media.id],
            body,
            channel_ids: this.mentionedChannels.map(channel => channel.id),
            context: {
                mail_post_autofollow: true,
            },
            message_type: 'comment',
            partner_ids: this.recipients.map(partner => partner.id),
        };
        if (this.subjectContent) {
            postData.subject = this.subjectContent;
        }
        let messageId;
        if (thread.model === 'mail.channel') {
            const command = this._getCommandFromText(body);
            Object.assign(postData, {
                command,
                subtype_xmlid: 'mail.mt_comment'
            });
            messageId = await this.async(() => this.env.services.rpc({
                model: 'mail.channel',
                method: command ? 'execute_command' : 'message_post',
                args: [thread.id],
                kwargs: postData,
            }));
        } else {
            Object.assign(postData, {
                subtype_xmlid: this.isLog ? 'mail.mt_note' : 'mail.mt_comment',
            });
            messageId = await this.async(() => this.env.services.rpc({
                model: thread.model,
                method: 'message_post',
                args: [thread.id],
                kwargs: postData,
            }));
            const [messageData] = await this.async(() => this.env.services.rpc({
                model: 'mail.message',
                method: 'message_format',
                args: [[messageId]],
            }));
            this.env.models['mail.message'].insert(Object.assign(
                {},
                this.env.models['mail.message'].convertData(messageData),
                {
                    originThread: [['insert', {
                        id: thread.id,
                        model: thread.model,
                    }]],
                })
            );
            thread.loadNewMessages();
        }
        for (const threadView of this.thread.threadViews) {
            // Reset auto scroll to be able to see the newly posted message.
            threadView.update({ hasAutoScrollOnMessageReceived: true });
        }
        thread.refreshFollowers();
        thread.fetchAndUpdateSuggestedRecipients();
        this._reset();
    },

});

});
