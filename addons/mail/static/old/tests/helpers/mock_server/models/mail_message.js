/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'mail/models/mail_message', {
    async _performRPC(route, args) {
        if (args.model === 'mail.message' && args.method === 'mark_all_as_read') {
            const domain = args.args[0] || args.kwargs.domain;
            return this._mockMailMessageMarkAllAsRead(domain);
        }
        if (args.model === 'mail.message' && args.method === 'message_format') {
            const ids = args.args[0];
            return this._mockMailMessageMessageFormat(ids);
        }
        if (args.model === 'mail.message' && args.method === 'set_message_done') {
            const ids = args.args[0];
            return this._mockMailMessageSetMessageDone(ids);
        }
        if (args.model === 'mail.message' && args.method === 'toggle_message_starred') {
            const ids = args.args[0];
            return this._mockMailMessageToggleMessageStarred(ids);
        }
        if (args.model === 'mail.message' && args.method === 'unstar_all') {
            return this._mockMailMessageUnstarAll();
        }
        return this._super(route, args);
    },
    /**
     * Simulates `mark_all_as_read` on `mail.message`.
     *
     * @private
     * @param {Array[]} [domain]
     * @returns {integer[]}
     */
    _mockMailMessageMarkAllAsRead(domain) {
        const notifDomain = [
            ['res_partner_id', '=', this.currentPartnerId],
            ['is_read', '=', false],
        ];
        if (domain) {
            const messages = this.getRecords('mail.message', domain);
            const ids = messages.map(messages => messages.id);
            this._mockMailMessageSetMessageDone(ids);
            return ids;
        }
        const notifications = this.getRecords('mail.notification', notifDomain);
        this.pyEnv['mail.notification'].write(
            notifications.map(notification => notification.id),
            { is_read: true },
        );
        const messageIds = [];
        for (const notification of notifications) {
            if (!messageIds.includes(notification.mail_message_id)) {
                messageIds.push(notification.mail_message_id);
            }
        }
        const messages = this.getRecords('mail.message', [['id', 'in', messageIds]]);
        // simulate compute that should be done based on notifications
        for (const message of messages) {
            this.pyEnv['mail.message'].write(
                [message.id],
                {
                    needaction: false,
                    needaction_partner_ids: message.needaction_partner_ids.filter(
                        partnerId => partnerId !== this.currentPartnerId
                    ),
                },
            );
        }
        this.pyEnv['bus.bus']._sendone(this.pyEnv.currentPartner, 'mail.message/mark_as_read', {
            'message_ids': messageIds,
            'needaction_inbox_counter': this._mockResPartner_GetNeedactionCount(this.currentPartnerId),
        });
        return messageIds;
    },
    /**
     * Simulates `_message_fetch` on `mail.message`.
     *
     * @private
     * @param {Array[]} domain
     * @param {integer} [max_id]
     * @param {integer} [min_id]
     * @param {integer} [limit=30]
     * @returns {Object[]}
     */
    _mockMailMessage_MessageFetch(domain, max_id, min_id, limit = 30) {
        if (max_id) {
            domain.push(['id', '<', max_id]);
        }
        if (min_id) {
            domain.push(['id', '>', min_id]);
        }
        let messages = this.getRecords('mail.message', domain);
        // sorted from highest ID to lowest ID (i.e. from youngest to oldest)
        messages.sort(function (m1, m2) {
            return m1.id < m2.id ? 1 : -1;
        });
        // pick at most 'limit' messages
        messages.length = Math.min(messages.length, limit);
        return messages;
    },
    /**
     * Simulates `message_format` on `mail.message`.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailMessageMessageFormat(ids) {
        const messages = this.getRecords('mail.message', [['id', 'in', ids]]);
        // sorted from highest ID to lowest ID (i.e. from most to least recent)
        messages.sort(function (m1, m2) {
            return m1.id < m2.id ? 1 : -1;
        });
        return messages.map(message => {
            const thread = message.model && this.getRecords(message.model, [
                ['id', '=', message.res_id],
            ])[0];
            let formattedAuthor;
            if (message.author_id) {
                const [author] = this.getRecords('res.partner', [['id', '=', message.author_id]], { active_test: false });
                formattedAuthor = {
                    'id': author.id,
                    'name': author.name,
                };
            } else {
                formattedAuthor = [['clear']];
            }
            const attachments = this.getRecords('ir.attachment', [
                ['id', 'in', message.attachment_ids],
            ]);
            const formattedAttachments = this._mockIrAttachment_attachmentFormat(attachments.map(attachment => attachment.id));
            const allNotifications = this.getRecords('mail.notification', [
                ['mail_message_id', '=', message.id],
            ]);
            const historyPartnerIds = allNotifications
                .filter(notification => notification.is_read)
                .map(notification => notification.res_partner_id);
            const needactionPartnerIds = allNotifications
                .filter(notification => !notification.is_read)
                .map(notification => notification.res_partner_id);
            let notifications = this._mockMailNotification_FilteredForWebClient(
                allNotifications.map(notification => notification.id)
            );
            notifications = this._mockMailNotification_NotificationFormat(
                notifications.map(notification => notification.id)
            );
            const trackingValueIds = this.getRecords('mail.tracking.value', [
                ['id', 'in', message.tracking_value_ids],
            ]);
            const formattedTrackingValues = this._mockMailTrackingValue_TrackingValueFormat(trackingValueIds);
            const partners = this.getRecords(
                'res.partner',
                [['id', 'in', message.partner_ids]],
            );
            const linkPreviews = this.getRecords('mail.link.preview', [
                ['id', 'in', message.link_preview_ids],
            ]);
            const linkPreviewsFormatted = linkPreviews.map(linkPreview => this._mockMailLinkPreviewFormat(linkPreview));

            const response = Object.assign({}, message, {
                attachment_ids: formattedAttachments,
                author: formattedAuthor,
                history_partner_ids: historyPartnerIds,
                linkPreviews: linkPreviewsFormatted,
                needaction_partner_ids: needactionPartnerIds,
                notifications,
                parentMessage: message.parent_id ? this._mockMailMessageMessageFormat([message.parent_id])[0] : false,
                recipients: partners.map(p => ({ id: p.id, name: p.name })),
                record_name: thread && (thread.name !== undefined ? thread.name : thread.display_name),
                trackingValues: formattedTrackingValues,
            });
            delete response['author_id'];
            if (message.subtype_id) {
                const subtype = this.getRecords('mail.message.subtype', [
                    ['id', '=', message.subtype_id],
                ])[0];
                response.subtype_description = subtype.description;
            }
            if (message.author_guest_id) {
                const [guest] = this.pyEnv['mail.guest'].searchRead([['id', '=', message.author_guest_id]]);
                response['guestAuthor'] = { id: guest.id, name: guest.name };
            }
            return response;
        });
    },
    /**
     * Simulates `_message_notification_format` on `mail.message`.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailMessage_MessageNotificationFormat(ids) {
        const messages = this.getRecords('mail.message', [['id', 'in', ids]]);
        return messages.map(message => {
            let notifications = this.getRecords('mail.notification', [
                ['mail_message_id', '=', message.id],
            ]);
            notifications = this._mockMailNotification_FilteredForWebClient(
                notifications.map(notification => notification.id)
            );
            notifications = this._mockMailNotification_NotificationFormat(
                notifications.map(notification => notification.id)
            );
            return {
                'date': message.date,
                'id': message.id,
                'message_type': message.message_type,
                'model': message.model,
                'notifications': notifications,
                'res_id': message.res_id,
                'res_model_name': message.res_model_name,
            };
        });
    },
    /**
     * Simulates `set_message_done` on `mail.message`, which turns provided
     * needaction message to non-needaction (i.e. they are marked as read from
     * from the Inbox mailbox). Also notify on the longpoll bus that the
     * messages have been marked as read, so that UI is updated.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockMailMessageSetMessageDone(ids) {
        const messages = this.getRecords('mail.message', [['id', 'in', ids]]);

        const notifications = this.getRecords('mail.notification', [
            ['res_partner_id', '=', this.currentPartnerId],
            ['is_read', '=', false],
            ['mail_message_id', 'in', messages.map(messages => messages.id)]
        ]);
        this.pyEnv['mail.notification'].write(
            notifications.map(notification => notification.id),
            { is_read: true },
        );
        // simulate compute that should be done based on notifications
        for (const message of messages) {
            this.pyEnv['mail.message'].write(
                [message.id],
                {
                    needaction: false,
                    needaction_partner_ids: message.needaction_partner_ids.filter(
                        partnerId => partnerId !== this.currentPartnerId
                    ),
                },
            );
            this.pyEnv['bus.bus']._sendone(this.pyEnv.currentPartner, 'mail.message/mark_as_read', {
                'message_ids': [message.id],
                'needaction_inbox_counter': this._mockResPartner_GetNeedactionCount(this.currentPartnerId),
            });
        }
    },
    /**
     * Simulates `toggle_message_starred` on `mail.message`.
     *
     * @private
     * @returns {integer[]} ids
     */
    _mockMailMessageToggleMessageStarred(ids) {
        const messages = this.getRecords('mail.message', [['id', 'in', ids]]);
        for (const message of messages) {
            const wasStared = message.starred_partner_ids.includes(this.currentPartnerId);
            this.pyEnv['mail.message'].write(
                [message.id],
                { starred_partner_ids: [[wasStared ? 3 : 4, this.currentPartnerId]] }
            );
            this.pyEnv['bus.bus']._sendone(this.pyEnv.currentPartner, 'mail.message/toggle_star', {
                'message_ids': [message.id],
                'starred': !wasStared,
            });
        }
    },
    /**
     * Simulates `unstar_all` on `mail.message`.
     *
     * @private
     */
    _mockMailMessageUnstarAll() {
        const messages = this.getRecords('mail.message', [
            ['starred_partner_ids', 'in', this.currentPartnerId],
        ]);
        this.pyEnv['mail.message'].write(
            messages.map(message => message.id),
            { starred_partner_ids: [[3, this.currentPartnerId]] }
        );
        this.pyEnv['bus.bus']._sendone(this.pyEnv.currentPartner, 'mail.message/toggle_star', {
            'message_ids': messages.map(message => message.id),
            'starred': false,
        });
    },
});
