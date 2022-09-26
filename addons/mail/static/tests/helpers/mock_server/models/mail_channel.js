/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

import { datetime_to_str } from 'web.time';

patch(MockServer.prototype, 'mail/models/mail_channel', {
    async _performRPC(route, args) {
        if (args.model === 'mail.channel' && args.method === 'action_unfollow') {
            const ids = args.args[0];
            return this._mockMailChannelActionUnfollow(ids);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_fetched') {
            const ids = args.args[0];
            return this._mockMailChannelChannelFetched(ids);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_fetch_preview') {
            const ids = args.args[0];
            return this._mockMailChannelChannelFetchPreview(ids);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_fold') {
            const ids = args.args[0];
            const state = args.args[1] || args.kwargs.state;
            return this._mockMailChannelChannelFold(ids, state);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_get') {
            const partners_to = args.args[0] || args.kwargs.partners_to;
            const pin = args.args[1] !== undefined
                ? args.args[1]
                : args.kwargs.pin !== undefined
                    ? args.kwargs.pin
                    : undefined;
            return this._mockMailChannelChannelGet(partners_to, pin);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_info') {
            const ids = args.args[0];
            return this._mockMailChannelChannelInfo(ids);
        }
        if (args.model === 'mail.channel' && args.method === 'add_members') {
            const ids = args.args[0];
            const partner_ids = args.args[1] || args.kwargs.partner_ids;
            return this._mockMailChannelAddMembers(ids, partner_ids);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_pin') {
            const ids = args.args[0];
            const pinned = args.args[1] || args.kwargs.pinned;
            return this._mockMailChannelChannelPin(ids, pinned);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_rename') {
            const ids = args.args[0];
            const name = args.args[1] || args.kwargs.name;
            return this._mockMailChannelChannelRename(ids, name);
        }
        if (route === '/mail/channel/set_last_seen_message') {
            const id = args.channel_id;
            const last_message_id = args.last_message_id;
            return this._mockMailChannel_ChannelSeen([id], last_message_id);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_set_custom_name') {
            const ids = args.args[0];
            const name = args.args[1] || args.kwargs.name;
            return this._mockMailChannelChannelSetCustomName(ids, name);
        }
        if (args.model === 'mail.channel' && args.method === 'create_group') {
            const partners_to = args.args[0] || args.kwargs.partners_to;
            return this._mockMailChannelCreateGroup(partners_to);
        }
        if (args.model === 'mail.channel' && args.method === 'execute_command_leave') {
            return this._mockMailChannelExecuteCommandLeave(args);
        }
        if (args.model === 'mail.channel' && args.method === 'execute_command_who') {
            return this._mockMailChannelExecuteCommandWho(args);
        }
        if (args.model === 'mail.channel' && args.method === 'write' && 'image_128' in args.args[1]) {
            const ids = args.args[0];
            return this._mockMailChannelWriteImage128(ids[0]);
        }
        if (args.model === 'mail.channel' && args.method === 'load_more_members') {
            const [channel_ids] = args.args;
            const { known_member_ids } = args.kwargs;
            return this._mockMailChannelLoadMoreMembers(channel_ids, known_member_ids);
        }
        if (args.model === 'mail.channel' && args.method === 'get_mention_suggestions') {
            return this._mockMailChannelGetMentionSuggestions(args);
        }
        return this._super(route, args);
    },
    /**
     * Simulates `message_post` on `mail.channel`.
     *
     * @private
     * @param {integer} id
     * @param {Object} kwargs
     * @param {Object} [context]
     * @returns {integer|false}
     */
    _mockMailChannelMessagePost(id, kwargs, context) {
        const message_type = kwargs.message_type || 'notification';
        const channel = this.getRecords('mail.channel', [['id', '=', id]])[0];
        if (channel.channel_type !== 'channel') {
            const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', '=', channel.id], ['partner_id', '=', this.currentPartnerId]]);
            this.pyEnv['mail.channel.member'].write(
                [memberOfCurrentUser.id],
                {
                    last_interest_dt: datetime_to_str(new Date()),
                    is_pinned: true,
                },
            );
        }
        const messageData = this._mockMailThreadMessagePost(
            'mail.channel',
            [id],
            Object.assign(kwargs, {
                message_type,
            }),
            context,
        );
        if (kwargs.author_id === this.currentPartnerId) {
            this._mockMailChannel_SetLastSeenMessage([channel.id], messageData.id);
        }
        // simulate compute of message_unread_counter
        const otherMembers = this.getRecords('mail.channel.member', [['channel_id', '=', channel.id], ['partner_id', '!=', this.currentPartnerId]]);
        for (const member of otherMembers) {
            this.pyEnv['mail.channel.member'].write(
                [member.id],
                { message_unread_counter: member.message_unread_counter + 1 },
            );
        }
        return messageData;
    },
    /**
     * Simulates `action_unfollow` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockMailChannelActionUnfollow(ids) {
        const channel = this.getRecords('mail.channel', [['id', 'in', ids]])[0];
        const [channelMember] = this.getRecords('mail.channel.member', [['channel_id', 'in', ids], ['partner_id', '=', this.currentPartnerId]]);
        if (!channelMember) {
            return true;
        }
        this.pyEnv['mail.channel'].write(
            [channel.id],
            {
                channel_member_ids: [[2, channelMember.id]],
            },
        );
        this.pyEnv['bus.bus']._sendone(this.pyEnv.currentPartner, 'mail.channel/leave', {
            'id': channel.id,
        });
        /**
         * Leave message not posted here because it would send the new message
         * notification on a separate bus notification list from the unsubscribe
         * itself which would lead to the channel being pinned again (handler
         * for unsubscribe is weak and is relying on both of them to be sent
         * together on the bus).
         */
        // this._mockMailChannelMessagePost(channel.id, {
        //     author_id: this.currentPartnerId,
        //     body: '<div class="o_mail_notification">left the channel</div>',
        //     subtype_xmlid: "mail.mt_comment",
        // });
        return true;
    },
    /**
     * Simulates `add_members` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @param {integer[]} partner_ids
     */
    _mockMailChannelAddMembers(ids, partner_ids) {
        const [channel] = this.getRecords('mail.channel', [['id', 'in', ids]]);
        const partners = this.getRecords('res.partner', [['id', 'in', partner_ids]]);
        for (const partner of partners) {
            this.pyEnv['mail.channel.member'].create({
                channel_id: channel.id,
                partner_id: partner.id,
            });
            const body = `<div class="o_mail_notification">invited ${partner.name} to the channel</div>`;
            const message_type = "notification";
            const subtype_xmlid = "mail.mt_comment";
            this._mockMailChannelMessagePost(
                channel.id,
                { body, message_type, subtype_xmlid },
            );
        }
        this.pyEnv['bus.bus']._sendone(channel, 'mail.channel/joined', {
            'channel': this._mockMailChannelChannelInfo([channel.id])[0],
            'invited_by_user_id': this.currentUserId,
        });
    },
    /**
     * Simulates `_broadcast` on `mail.channel`.
     *
     * @private
     * @param {integer} id
     * @param {integer[]} partner_ids
     * @returns {Object}
     */
    _mockMailChannel_broadcast(ids, partner_ids) {
        const notifications = this._mockMailChannel_channelChannelNotifications(ids, partner_ids);
        this.pyEnv['bus.bus']._sendmany(notifications);
    },
    /**
     * Simulates `_channel_channel_notifications` on `mail.channel`.
     *
     * @private
     * @param {integer} id
     * @param {integer[]} partner_ids
     * @returns {Object}
     */
    _mockMailChannel_channelChannelNotifications(ids, partner_ids) {
        const notifications = [];
        for (const partner_id of partner_ids) {
            const user = this.getRecords('res.users', [['partner_id', 'in', partner_id]])[0];
            if (!user) {
                continue;
            }
            // Note: `channel_info` on the server is supposed to be called with
            // the proper user context but this is not done here for simplicity.
            const channelInfos = this._mockMailChannelChannelInfo(ids);
            const [relatedPartner] = this.pyEnv['res.partner'].searchRead([['id', '=', partner_id]]);
            for (const channelInfo of channelInfos) {
                notifications.push([relatedPartner, 'mail.channel/legacy_insert', channelInfo]);
            }
        }
        return notifications;
    },
    /**
     * Simulates `channel_fetched` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @param {string} extra_info
     */
    _mockMailChannelChannelFetched(ids) {
        const channels = this.getRecords('mail.channel', [['id', 'in', ids]]);
        for (const channel of channels) {
            const channelMessages = this.getRecords('mail.message', [
                ['model', '=', 'mail.channel'],
                ['res_id', '=', channel.id],
            ]);
            const lastMessage = channelMessages.reduce((lastMessage, message) => {
                if (message.id > lastMessage.id) {
                    return message;
                }
                return lastMessage;
            }, channelMessages[0]);
            if (!lastMessage) {
                continue;
            }
            const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', '=', channel.id], ['partner_id', '=', this.currentPartnerId]]);
            this.pyEnv['mail.channel.member'].write(
                [memberOfCurrentUser.id],
                { fetched_message_id: lastMessage.id },
            );
            this.pyEnv['bus.bus']._sendone(channel, 'mail.channel.member/fetched', {
                'channel_id': channel.id,
                'id': memberOfCurrentUser.id,
                'last_message_id': lastMessage.id,
                'partner_id': this.currentPartnerId,
            });
        }
    },
    /**
     * Simulates `channel_fetch_preview` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object[]} list of channels previews
     */
    _mockMailChannelChannelFetchPreview(ids) {
        const channels = this.getRecords('mail.channel', [['id', 'in', ids]]);
        return channels.map(channel => {
            const channelMessages = this.getRecords('mail.message', [
                ['model', '=', 'mail.channel'],
                ['res_id', '=', channel.id],
            ]);
            const lastMessage = channelMessages.reduce((lastMessage, message) => {
                if (message.id > lastMessage.id) {
                    return message;
                }
                return lastMessage;
            }, channelMessages[0]);
            return {
                id: channel.id,
                last_message: lastMessage ? this._mockMailMessageMessageFormat([lastMessage.id])[0] : false,
            };
        });
    },
    /**
     * Simulates the 'channel_fold' route on `mail.channel`.
     * In particular sends a notification on the bus.
     *
     * @private
     * @param {number} ids
     * @param {state} [state]
     */
    _mockMailChannelChannelFold(ids, state) {
        const channels = this.getRecords('mail.channel', [['id', 'in', ids]]);
        for (const channel of channels) {
            const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', '=', channel.id], ['partner_id', '=', this.currentPartnerId]]);
            const foldState = state ? state : memberOfCurrentUser.fold_state === 'open' ? 'folded' : 'open';
            const vals = {
                fold_state: foldState,
                is_minimized: foldState !== 'closed',
            };
            this.pyEnv['mail.channel.member'].write([memberOfCurrentUser.id], vals);
            this.pyEnv['bus.bus']._sendone(this.pyEnv.currentPartner, 'mail.thread/insert', {
                'id': channel.id,
                'model': 'mail.channel',
                'serverFoldState': memberOfCurrentUser.fold_state,
            });
        }
    },
    /**
     * Simulates 'channel_get' on 'mail.channel'.
     *
     * @private
     * @param {integer[]} [partners_to=[]]
     * @param {boolean} [pin=true]
     * @returns {Object}
     */
    _mockMailChannelChannelGet(partners_to = [], pin = true) {
        if (partners_to.length === 0) {
            return false;
        }
        if (!partners_to.includes(this.currentPartnerId)) {
            partners_to.push(this.currentPartnerId);
        }
        const partners = this.getRecords('res.partner', [['id', 'in', partners_to]]);
        // NOTE: this mock is not complete, which is done for simplicity.
        // Indeed if a chat already exists for the given partners, the server
        // is supposed to return this existing chat. But the mock is currently
        // always creating a new chat, because no test is relying on receiving
        // an existing chat.
        const id = this.pyEnv['mail.channel'].create({
            channel_member_ids: partners.map(partner => [0, 0, {
                partner_id: partner.id,
            }]),
            channel_type: 'chat',
            name: partners.map(partner => partner.name).join(", "),
        });
        return this._mockMailChannelChannelInfo([id])[0];
    },
    /**
     * Simulates `channel_info` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailChannelChannelInfo(ids) {
        const channels = this.getRecords('mail.channel', [['id', 'in', ids]]);
        return channels.map(channel => {
            const members = this.getRecords('mail.channel.member', [['id', 'in', channel.channel_member_ids]]);
            const messages = this.getRecords('mail.message', [
                ['model', '=', 'mail.channel'],
                ['res_id', '=', channel.id],
            ]);
            const [group_public_id] = this.getRecords('res.groups', [
                ['id', '=', channel.group_public_id],
            ]);
            const lastMessageId = messages.reduce((lastMessageId, message) => {
                if (!lastMessageId || message.id > lastMessageId) {
                    return message.id;
                }
                return lastMessageId;
            }, undefined);
            const messageNeedactionCounter = this.getRecords('mail.notification', [
                ['res_partner_id', '=', this.currentPartnerId],
                ['is_read', '=', false],
                ['mail_message_id', 'in', messages.map(message => message.id)],
            ]).length;
            const channelData = {
                avatarCacheKey: channel.avatarCacheKey,
                channel_type: channel.channel_type,
                id: channel.id,
                memberCount: channel.member_count,
            };
            const res = Object.assign({}, channel, {
                last_message_id: lastMessageId,
                message_needaction_counter: messageNeedactionCounter,
                authorizedGroupFullName: group_public_id ? group_public_id.name : false,
            });
            const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', '=', channel.id], ['partner_id', '=', this.currentPartnerId]]);
            if (memberOfCurrentUser) {
                Object.assign(res, {
                    is_minimized: memberOfCurrentUser.is_minimized,
                    is_pinned: memberOfCurrentUser.is_pinned,
                    last_interest_dt: memberOfCurrentUser.last_interest_dt,
                    message_unread_counter: memberOfCurrentUser.message_unread_counter,
                    state: memberOfCurrentUser.fold_state || 'open',
                });
                Object.assign(channelData, {
                    custom_channel_name: memberOfCurrentUser.custom_channel_name,
                    serverMessageUnreadCounter: memberOfCurrentUser.message_unread_counter,
                });
                if (memberOfCurrentUser.rtc_inviting_session_id) {
                    res['rtc_inviting_session'] = { 'id': memberOfCurrentUser.rtc_inviting_session_id };
                }
                channelData['channelMembers'] = [['insert', this._mockMailChannelMember_MailChannelMemberFormat([memberOfCurrentUser.id])]];
            }
            if (channel.channel_type !== 'channel') {
                res['seen_partners_info'] = members.filter(member => member.partner_id).map(member => {
                    return {
                        partner_id: member.partner_id,
                        seen_message_id: member.seen_message_id,
                        fetched_message_id: member.fetched_message_id,
                    };
                });
                channelData['channelMembers'] = [['insert', this._mockMailChannelMember_MailChannelMemberFormat(members.map(member => member.id))]];
            }
            res.channel = channelData;
            return res;
        });
    },
    /**
     * Simulates the `channel_pin` method of `mail.channel`.
     *
     * @private
     * @param {number[]} ids
     * @param {boolean} [pinned=false]
     */
    async _mockMailChannelChannelPin(ids, pinned = false) {
        const [channel] = this.getRecords('mail.channel', [['id', 'in', ids]]);
        const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', '=', channel.id], ['partner_id', '=', this.currentPartnerId], ['is_pinned', '!=', pinned]]);
        if (memberOfCurrentUser) {
            this.pyEnv['mail.channel.member'].write(
                [memberOfCurrentUser.id],
                { is_pinned: pinned },
            );
        }
        if (!pinned) {
            this.pyEnv['bus.bus']._sendone(this.pyEnv.currentPartner, 'mail.channel/unpin', {
                'id': channel.id,
            });
        } else {
            this.pyEnv['bus.bus']._sendone(this.pyEnv.currentPartner, 'mail.channel/legacy_insert', this._mockMailChannelChannelInfo([channel.id])[0]);
        }
    },
    /**
     * Simulates the `_channel_seen` method of `mail.channel`.
     *
     * @private
     * @param integer[] ids
     * @param {integer} last_message_id
     */
    async _mockMailChannel_ChannelSeen(ids, last_message_id) {
        // Update record
        const channel_id = ids[0];
        if (!channel_id) {
            throw new Error('Should only be one channel in channel_seen mock params');
        }
        const channel = this.getRecords('mail.channel', [['id', '=', channel_id]])[0];
        const messagesBeforeGivenLastMessage = this.getRecords('mail.message', [
            ['id', '<=', last_message_id],
            ['model', '=', 'mail.channel'],
            ['res_id', '=', channel.id],
        ]);
        if (!messagesBeforeGivenLastMessage || messagesBeforeGivenLastMessage.length === 0) {
            return;
        }
        if (!channel) {
            return;
        }
        const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', '=', channel_id], ['partner_id', '=', this.currentPartnerId]]);
        if (memberOfCurrentUser.seen_message_id && memberOfCurrentUser.seen_message_id >= last_message_id) {
            return;
        }
        this._mockMailChannel_SetLastSeenMessage([channel.id], last_message_id);
        this.pyEnv['bus.bus']._sendone(channel.channel_type === 'chat' ? channel : this.pyEnv.currentPartner, 'mail.channel.member/seen', {
            'channel_id': channel.id,
            'last_message_id': last_message_id,
            'partner_id': this.currentPartnerId,
        });
    },
    /**
     * Simulates `channel_rename` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockMailChannelChannelRename(ids, name) {
        const channel = this.getRecords('mail.channel', [['id', 'in', ids]])[0];
        this.pyEnv['mail.channel'].write(
            [channel.id],
            { name },
        );
        this.pyEnv['bus.bus']._sendone(channel, 'mail.thread/insert', {
            'id': channel.id,
            'model': 'mail.channel',
            'name': name,
        });
    },
    /**
     * Simulates `channel_set_custom_name` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockMailChannelChannelSetCustomName(ids, name) {
        const channelId = ids[0]; // simulate ensure_one.
        const [memberIdOfCurrentUser] = this.pyEnv['mail.channel.member'].search([['partner_id', '=', this.currentPartnerId], ['channel_id', '=', channelId]]);
        this.pyEnv['mail.channel.member'].write(
            [memberIdOfCurrentUser],
            { custom_channel_name: name },
        );
        this.pyEnv['bus.bus']._sendone(this.pyEnv.currentPartner, 'mail.channel/insert', {
            'custom_channel_name': name,
            'id': channelId,
        });
    },
    /**
     * Simulates the `create_group` on `mail.channel`.
     *
     * @private
     * @param {integer[]} partners_to
     * @returns {Object}
     */
    async _mockMailChannelCreateGroup(partners_to) {
        const partners = this.getRecords('res.partner', [['id', 'in', partners_to]]);
        const id = this.pyEnv['mail.channel'].create({
            channel_type: 'group',
            channel_member_ids: partners.map(partner => [0, 0, { partner_id: partner.id }]),
            name: '',
        });
        this._mockMailChannel_broadcast(id, partners.map(partner => partner.id));
        return this._mockMailChannelChannelInfo([id])[0];
    },
    /**
     * Simulates `execute_command_leave` on `mail.channel`.
     *
     * @private
     */
    _mockMailChannelExecuteCommandLeave(args) {
        const channel = this.getRecords('mail.channel', [['id', 'in', args.args[0]]])[0];
        if (channel.channel_type === 'channel') {
            this._mockMailChannelActionUnfollow([channel.id]);
        } else {
            this._mockMailChannelChannelPin(channel.uuid, false);
        }
    },
    /**
     * Simulates `execute_command_who` on `mail.channel`.
     *
     * @private
     */
    _mockMailChannelExecuteCommandWho(args) {
        const ids = args.args[0];
        const channels = this.getRecords('mail.channel', [['id', 'in', ids]]);
        for (const channel of channels) {
            const members = this.getRecords('mail.channel.member', [['id', 'in', channel.channel_member_ids]]);
            const otherPartnerIds = members.filter(member => member.partner_id && member.partner_id !== this.currentPartnerId).map(member => member.partner_id);
            const otherPartners = this.getRecords('res.partner', [['id', 'in', otherPartnerIds]]);
            let message = "You are alone in this channel.";
            if (otherPartners.length > 0) {
                message = `Users in this channel: ${otherPartners.map(partner => partner.name).join(', ')} and you`;
            }
            this.pyEnv['bus.bus']._sendone(this.pyEnv.currentPartner, 'mail.channel/transient_message', {
                'body': `<span class="o_mail_notification">${message}</span>`,
                'model': 'mail.channel',
                'res_id': channel.id,
            });
        }
    },
    /**
     * Simulates `get_mention_suggestions` on `mail.channel`.
     *
     * @private
     * @returns {Array[]}
     */
    _mockMailChannelGetMentionSuggestions(args) {
        const search = args.kwargs.search || '';
        const limit = args.kwargs.limit || 8;

        /**
         * Returns the given list of channels after filtering it according to
         * the logic of the Python method `get_mention_suggestions` for the
         * given search term. The result is truncated to the given limit and
         * formatted as expected by the original method.
         *
         * @param {Object[]} channels
         * @param {string} search
         * @param {integer} limit
         * @returns {Object[]}
         */
        const mentionSuggestionsFilter = function (channels, search, limit) {
            const matchingChannels = channels
                .filter(channel => {
                    // no search term is considered as return all
                    if (!search) {
                        return true;
                    }
                    // otherwise name or email must match search term
                    if (channel.name && channel.name.includes(search)) {
                        return true;
                    }
                    return false;
                }).map(channel => {
                    // expected format
                    return {
                        authorizedGroupFullName: channel.group_public_id ? channel.group_public_id.name : false,
                        channel: {
                            channel_type: channel.channel_type,
                            id: channel.id,
                        },
                        id: channel.id,
                        name: channel.name,
                    };
                });
            // reduce results to max limit
            matchingChannels.length = Math.min(matchingChannels.length, limit);
            return matchingChannels;
        };

        const mentionSuggestions = mentionSuggestionsFilter(this.models['mail.channel'].records, search, limit);

        return mentionSuggestions;
    },
    /**
     * Simulates `write` on `mail.channel` when `image_128` changes.
     *
     * @param {integer} id
     */
    _mockMailChannelWriteImage128(id) {
        this.pyEnv['mail.channel'].write(
            [id],
            {
                avatarCacheKey: moment.utc().format("YYYYMMDDHHmmss"),
            },
        );
        const channel = this.pyEnv['mail.channel'].searchRead([['id', '=', id]])[0];
        this.pyEnv['bus.bus']._sendone(channel, 'mail.channel/insert', {
            'avatarCacheKey': channel.avatarCacheKey,
            'id': id,
        });
    },
    /**
     * Simulates `load_more_members` on `mail.channel`.
     *
     * @private
     * @param {integer[]} channel_ids
     * @param {integer[]} known_member_ids
     */
    _mockMailChannelLoadMoreMembers(channel_ids, known_member_ids) {
        const members = this.pyEnv['mail.channel.member'].searchRead([
            ['id', 'not in', known_member_ids],
            ['channel_id', 'in', channel_ids],
        ], { limit: 100 });
        const memberCount = this.pyEnv['mail.channel.member'].searchCount([
            ['channel_id', 'in', channel_ids],
        ]);
        const membersData = [];
        for (const member of members) {
            let persona;
            if (member.partner_id) {
                const [partner] = this.pyEnv['res.partner'].searchRead(
                    [['id', '=', member.partner_id[0]]],
                    { fields: ['id', 'name', 'im_status'] }
                );
                persona = {
                    'partner': {
                        'id': partner.id,
                        'name': partner.name,
                        'im_status': partner.im_status,
                    },
                };
            }
            if (member.guest_id) {
                const [guest] = this.pyEnv['mail.guest'].searchRead(
                    [['id', '=', member.guest_id[0]]],
                    { fields: ['id', 'name'] }
                );
                persona = {
                    'guest': {
                        'id': guest.id,
                        'name': guest.name,
                    },
                };
            }
            membersData.push({
                'id': member.id,
                'persona': persona,
            });
        }
        return {
            channelMembers: [['insert', membersData]],
            memberCount,
        };
    },
    /**
     * Simulates the `_set_last_seen_message` method of `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @param {integer} message_id
     */
    _mockMailChannel_SetLastSeenMessage(ids, message_id) {
        const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', 'in', ids], ['partner_id', '=', this.currentPartnerId]]);
        this.pyEnv['mail.channel.member'].write([memberOfCurrentUser.id], {
            fetched_message_id: message_id,
            seen_message_id: message_id,
        });
    },
});
