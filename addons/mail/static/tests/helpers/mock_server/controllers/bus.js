/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'mail/controllers/bus', {
    /**
     * @override
     */
    async _performRPC(route, args) {
        if (route === '/mail/chat_post') {
            const uuid = args.uuid;
            const message_content = args.message_content;
            const context = args.context;
            return this._mockRouteMailChatPost(uuid, message_content, context);
        }
        return this._super(route, args);
    },
    /**
     * Simulates the `/mail/chat_post` route.
     *
     * @private
     * @param {string} uuid
     * @param {string} message_content
     * @param {Object} [context={}]
     * @returns {Object} one key for list of followers and one for subtypes
     */
    async _mockRouteMailChatPost(uuid, message_content, context = {}) {
        const mailChannel = this.getRecords('mail.channel', [['uuid', '=', uuid]])[0];
        if (!mailChannel) {
            return false;
        }

        let user_id;
        // find the author from the user session
        if ('mockedUserId' in context) {
            // can be falsy to simulate not being logged in
            user_id = context.mockedUserId;
        } else {
            user_id = this.currentUserId;
        }
        let author_id;
        let email_from;
        if (user_id) {
            const author = this.getRecords('res.users', [['id', '=', user_id]])[0];
            author_id = author.partner_id;
            email_from = `${author.display_name} <${author.email}>`;
        } else {
            author_id = false;
            // simpler fallback than catchall_formatted
            email_from = mailChannel.anonymous_name || "catchall@example.com";
        }
        // supposedly should convert plain text to html
        const body = message_content;
        // ideally should be posted with mail_create_nosubscribe=True
        return this._mockMailChannelMessagePost(
            mailChannel.id,
            {
                author_id,
                email_from,
                body,
                message_type: 'comment',
                subtype_xmlid: 'mail.mt_comment',
            },
            context
        );
    },
});
