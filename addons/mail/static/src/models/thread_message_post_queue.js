/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { link, clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'ThreadMessagePostQueue',
    identifyingFields: ['thread'],
    recordMethods: {
        /**
         * Insert a new message composition inside the message queue and start
         * to send message.
         *
         * @param {MessageComposition} compositionData
         */
        async add(compositionData) {
            const composition = this.messaging.models['MessageComposition'].insert(compositionData);
            this.update({ messagesToSend: link(composition) });
            if (composition.composerView.threadView) {
                composition.composerView.threadView.addComponentHint(
                    'message-received',
                    { message: composition.message }
                );
            }
            // Prevent multiple queue to run at the same time.
            if (this.isSending) {
                return;
            }
            this._process();
        },
        async _process() {
            this.update({ isSending: true });
            const composition = this.messagesToSend[0];
            await this.postMessage(composition);
            if (this.messagesToSend.length > 0) {
                return this._process();
            }
            return this.update({ isSending: false });
        },
        /**
         * Post a message in provided composer's thread based on current
         * composer fields values.
         */
        async postMessage(composition) {
            const composer = composition.composerView.composer;
            if (this.messaging.currentPartner) {
                composer.thread.unregisterCurrentPartnerIsTyping({ immediateNotify: true });
            }
            composition.generateBody();
            const postData = {
                attachment_ids: composition.message.attachments.map(attachment => attachment.id),
                body: composition.message.body,
                message_type: 'comment',
                partner_ids: composition.recipients.map(partner => partner.id),
            };
            const params = {
                post_data: postData,
                thread_id: composer.thread.id,
                thread_model: composer.thread.model,
                shadow: true,
            };
            try {
                if (composer.thread.model === 'mail.channel') {
                    Object.assign(postData, { subtype_xmlid: 'mail.mt_comment' });
                } else {
                    Object.assign(postData, {
                        subtype_xmlid: composer.isLog ? 'mail.mt_note' : 'mail.mt_comment',
                    });
                    if (!composer.isLog) {
                        params.context = { mail_post_autofollow: true };
                    }
                }
                if (composition.composerView.threadView && composition.composerView.threadView.replyingToMessageView && composition.composerView.threadView.thread !== this.messaging.inbox) {
                    postData.parent_id = composition.composerView.threadView.replyingToMessageView.message.id;
                }
                const { threadView = {} } = composition.composerView;
                const { thread: chatterThread } = composition.composerView.chatter || {};
                const { thread: threadViewThread } = threadView;
                const messageData = await this.env.services.rpc({ route: `/mail/message/post`, params });
                if (!this.messaging) {
                    return;
                }
                const composerView = composition.composerView;

                const messageConverted = this.messaging.models['Message'].convertData(messageData);
                this.messaging.modelManager._delete(composition.message);
                composition.update({
                    message: insertAndReplace(messageConverted),
                });

                for (const threadView of composition.message.originThread.threadViews) {
                    // Reset auto scroll to be able to see the newly posted message.
                    threadView.update({ hasAutoScrollOnMessageReceived: true });
                    threadView.addComponentHint('message-posted', { message: composition.message });
                }
                if (chatterThread && chatterThread.exists()) {
                    // Load new messages to fetch potential new messages from other users (useful due to lack of auto-sync in chatter).
                    chatterThread.fetchData(['followers', 'messages', 'suggestedRecipients']);
                }
                if (threadViewThread) {
                    if (threadViewThread === this.messaging.inbox) {
                        if (composerView) {
                            composerView.delete();
                        }
                        this.env.services['notification'].notify({
                            message: _.str.sprintf(this.env._t(`Message posted on "%s"`), composition.message.originThread.displayName),
                            type: 'info',
                        });
                    }
                    if (threadView && threadView.exists()) {
                        threadView.update({ replyingToMessageView: clear() });
                    }
                }
                composition.delete();
            } catch {
                this.update({
                    isSending: false,
                });
            }
        },
    },
    fields: {
        /**
         * State that the queue is currently sending message or not.
         */
        isSending: attr({
            default: false,
        }),
        messagesToSend: many('MessageComposition'),
        thread: one('Thread', {
            inverse: 'threadMessagePostQueue',
            required: true,
            readonly: true,
        }),
    },
});
