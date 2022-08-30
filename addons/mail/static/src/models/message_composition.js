/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one, many } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'MessageComposition',
    fields: {
        attachments: many('Attachment'),
        id: attr({
            identifying: true,
        }),
        chatter: one('Chatter'),
        composerView: one('ComposerView'),
        context: attr({
            compute: function () {
                if (this.isLog) {
                    return { mail_post_autofollow: this.thread.hasWriteAccess };
                }
                return clear();
            }
        }),
        body: attr(),
        message_type: attr({
            default: 'comment',
        }),
        isLog: attr(),
        subtype_xmlid: attr({
            compute() {
                if (this.thread.model === 'mail.channel') {
                    return 'mail.mt_comment';
                }
                return this.isLog ? 'mail.mt_note' : 'mail.mt_comment';
            }
        }),
        params: attr({
            compute() {
                return {
                    post_data: {
                        attachment_ids: this.attachments.map(attachment => attachment.id),
                        body: this.body,
                        message_type: this.message_type,
                        partner_ids: this.partners.map(partner => partner.id),
                        subtype_xmlid: this.subtype_xmlid,
                        parent_id: this.parent_id,
                    },
                    thread_id: this.thread.id,
                    thread_model: this.thread.model,
                };
            }
        }),
        parent_id: attr({
            compute() {
                if (this.threadView && this.threadView.replyingToMessageView && this.threadView.thread !== this.messaging.inbox.thread) {
                    return this.threadView.replyingToMessageView.message.id;
                }
                return clear();
            }
        }),
        partners: many('Partner'),
        thread: one('Thread'),
        threadView: one('ThreadView'),
    },
});
