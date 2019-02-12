odoo.define('mail.store.actions', function (require) {
"use strict";

const AttachmentViewer = require('mail.component.AttachmentViewer');
const emojis = require('mail.emojis');
const mailUtils = require('mail.utils');

const config = require('web.config');
const core = require('web.core');
const time = require('web.time');
const utils = require('web.utils');

const _t = core._t;

const actions = {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     */
    closeAllChatWindows({ dispatch, state }) {
        const chatWindowLocalIds = state.chatWindowManager.chatWindowLocalIds;
        for (const chatWindowLocalId of chatWindowLocalIds) {
            dispatch('closeChatWindow', chatWindowLocalId);
        }
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {string} chatWindowLocalId either 'new_message' or thread local
     *   Id, a valid Id in `chatWindowLocalIds` list of chat window manager.
     */
    closeChatWindow({ dispatch, state }, chatWindowLocalId) {
        const cwm = state.chatWindowManager;
        cwm.chatWindowLocalIds = cwm.chatWindowLocalIds.filter(id => id !== chatWindowLocalId);
        delete cwm.storedChatWindowStates[chatWindowLocalId];
        if (chatWindowLocalId !== 'new_message') {
            const thread = state.threads[chatWindowLocalId];
            Object.assign(thread, {
                is_minimized: false,
                state: 'closed',
            });
            dispatch('_notifyServerThreadState', thread.localId);
        }
        dispatch('_computeChatWindows');
    },
    /**
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {string} dialogId
     */
    closeDialog({ state }, dialogId) {
        state.dialogManager.dialogs =
            state.dialogManager.dialogs.filter(item => item.id !== dialogId);
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     */
    closeDiscuss({ dispatch, state }) {
        if (!state.discuss.isOpen) {
            return;
        }
        dispatch('updateDiscuss', {
            isOpen: false,
        });
        dispatch('_computeChatWindows');
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     */
    closeMessagingMenu({ dispatch }) {
        dispatch('updateMessagingMenu', {
            activeTabId: 'all',
            isMobileNewMessageToggled: false,
            isOpen: false,
        });
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} data
     * @param {string} data.filename
     * @param {integer} [data.id]
     * @param {boolean} [data.isTemporary=false]
     * @param {string} [data.mimetype]
     * @param {string} [data.name]
     * @param {integer} [data.size]
     * @return {string} attachment local Id
     */
    createAttachment({ dispatch, state }, data) {
        let {
            filename,
            id,
            isTemporary=false,
            mimetype,
            name,
            res_id,
            res_model,
            size,
        } = data;
        if (isTemporary) {
            id = state.attachmentNextTemporaryId;
            mimetype = '';
            state.attachmentNextTemporaryId--;
        }
        const attachment = {
            _model: 'ir.attachment',
            composerId: null,
            filename,
            id,
            isTemporary,
            localId: `ir.attachment_${id}`,
            messageLocalIds: [],
            mimetype,
            name,
            res_id,
            res_model,
            size,
        };
        state.attachments[attachment.localId] = attachment;
        // compute attachment links (--> attachment)
        if (isTemporary) {
            state.temporaryAttachmentLocalIds[attachment.filename] = attachment.localId;
        } else {
            // check if there is a temporary attachment linked to this attachment,
            // and remove + replace it in the composer at the correct position
            const temporaryAttachmentLocalId = state.temporaryAttachmentLocalIds[filename];
            if (temporaryAttachmentLocalId) {
                // change temporary attachment links with non-temporary one
                const temporaryAttachment = state.attachments[temporaryAttachmentLocalId];
                const composerId = temporaryAttachment.composerId;
                if (composerId) {
                    dispatch('_replaceAttachmentInComposer',
                        composerId,
                        temporaryAttachmentLocalId,
                        attachment.localId);
                }
                dispatch('deleteAttachment', temporaryAttachmentLocalId);
            }
        }
        return attachment.localId;
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {boolean} [param1.autoselect=false]
     * @param {string} param1.name
     * @param {integer|undefined} [param1.partnerId=undefined]
     * @param {string|undefined} [param1.public=undefined]
     * @param {string} param1.type
     */
    async createChannel(
        { dispatch, env, state },
        {
            autoselect=false,
            name,
            partnerId,
            public: publicStatus,
            type,
        }
    ) {
        const data = await env.rpc({
            model: 'mail.channel',
            method: type === 'chat' ? 'channel_get' : 'channel_create',
            args: type === 'chat' ? [[partnerId]] : [name, publicStatus],
            kwargs: {
                context: {
                    ...env.session.user_content,
                    isMobile: config.device.isMobile
                }
            }
        });
        const threadLocalId = dispatch('_createThread', { ...data });
        if (state.threads[threadLocalId].is_minimized) {
            dispatch('openThread', threadLocalId, {
                chatWindowMode: 'last',
            });
        }
        if (autoselect) {
            dispatch('openThread', threadLocalId);
        }
    },
    /**
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {string} composerId
     * @param {Object} [initialState={}]
     */
    createComposer({ state }, composerId, initialState={}) {
        state.composers[composerId] = initialState;
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {string} attachmentLocalId
     */
    deleteAttachment({ dispatch, state }, attachmentLocalId) {
        const attachment = state.attachments[attachmentLocalId];
        if (attachment.isTemporary) {
            delete state.temporaryAttachmentLocalIds[attachment.filename];
        }
        // remove attachment from composers
        for (const composerId in state.composers) {
            const composer = state.composers[composerId];
            if (composer.attachmentLocalIds.includes(attachmentLocalId)) {
                dispatch('_updateComposer', composerId, {
                    attachmentLocalIds:
                        composer.attachmentLocalIds.filter(localId =>
                            localId !== attachmentLocalId)
                });
            }
        }
        // remove attachment from messages
        for (const messageLocalId of attachment.messageLocalIds) {
            const message = state.messages[messageLocalId];
            if (!message.attachmentLocalIds.includes(attachmentLocalId)) {
                return;
            }
            dispatch('_unlinkAttachmentFromMessage', messageLocalId, attachmentLocalId);
        }
        delete state.attachments[attachmentLocalId];
    },
    /**
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {string} composerId
     */
    deleteComposer({ state }, composerId) {
        delete state.composers[composerId];
    },
    /**
     * Unused for the moment, but may be useful for moderation
     *
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {string} messageLocalId
     */
    deleteMessage({ dispatch, state }, messageLocalId) {
        delete state.messages[messageLocalId];
        for (const threadLocalId of Object.keys(state.threads)) {
            dispatch('_unlinkMessageFromThread', {
                messageLocalId,
                threadLocalId,
            });
        }
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param1
     * @param {integer} param1.resId
     * @param {string} param1.resModel
     */
    async fetchDocumentAttachments(
        { dispatch, env },
        { resId, resModel }
    ) {
        const attachmentsData = await env.rpc({
            model: 'ir.attachment',
            method: 'search_read',
            domain: [
                ['res_id', '=', resId],
                ['res_model', '=', resModel],
            ],
            fields: ['id', 'name', 'mimetype'],
        });
        for (const attachmentData of attachmentsData) {
            dispatch('_insertAttachment', {
                res_id: resId,
                res_model: resModel,
                ...attachmentData,
            });
        }
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {string} threadLocalId
     */
    async fetchSuggestedRecipientsOnThread(
        { dispatch, env, state },
        threadLocalId
    ) {
        const thread = state.threads[threadLocalId];
        const result = await env.rpc({
            route: '/mail/get_suggested_recipients',
            params: {
                model: thread._model,
                res_ids: [thread.id],
            },
        });
        const suggestedRecipients = result[thread.id].map(recipient => {
            const parsedEmail = recipient[1] && mailUtils.parseEmail(recipient[1]);
            const partnerLocalId = dispatch('_insertPartner', {
                display_name: recipient[1],
                email: parsedEmail[1],
                id: recipient[0],
                name: parsedEmail[0],
            });
            return {
                checked: true,
                partnerLocalId,
                reason: recipient[2],
            };
        });
        thread.suggestedRecipients = suggestedRecipients; // aku todo
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {string} chatWindowLocalId either 'new_message' or minimized
     *   thread local Id, a valid chat window in `chatWindowLocalIds` list of
     *   chat window manager
     */
    focusChatWindow(
        { dispatch, state },
        chatWindowLocalId
    ) {
        const cwm = state.chatWindowManager;
        const visibleChatWindowLocalIds =
            cwm.computed.visible.map(item => item.chatWindowLocalId);
        if (!visibleChatWindowLocalIds.includes(chatWindowLocalId)) {
            return;
        }
        dispatch('_updateChatWindowManager', {
            autofocusChatWindowLocalId: chatWindowLocalId,
            autofocusCounter: cwm.autofocusCounter + 1,
        });
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} data
     * @param {integer} data.globalWindowInnerHeight
     * @param {integer} data.globalWindowInnerWidth
     * @param {boolean} data.isMobile
     */
    handleGlobalWindowResize(
        { dispatch, state },
        data
    ) {
        const wasMobile = state.isMobile;
        const {
            globalWindowInnerHeight,
            globalWindowInnerWidth,
            isMobile,
        } = data;
        Object.assign(state.globalWindow, {
            innerHeight: globalWindowInnerHeight,
            innerWidth: globalWindowInnerWidth,
        });
        state.isMobile = isMobile; // from `config.device.isMobile`
        // update discuss
        if (
            state.isMobile &&
            !wasMobile &&
            state.discuss.isOpen &&
            state.discuss.activeThreadLocalId
        ) {
            const activeDiscussThread = state.threads[state.discuss.activeThreadLocalId];
            const newActiveMobileNavbarTabId =
                activeDiscussThread._model === 'mail.box' ? 'mailbox'
                : activeDiscussThread.channel_type === 'channel' ? 'channel'
                : activeDiscussThread.channel_type === 'chat' ? 'chat'
                : state.discuss.activeMobileNavbarTabId;
            dispatch('updateDiscuss', {
                activeMobileNavbarTabId: newActiveMobileNavbarTabId,
            });
        }
        // update docked chat windows
        dispatch('_computeChatWindows');
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param1
     * @param {function} param1.ready
     */
    async initMessaging(
        { dispatch, env },
        { ready }
    ) {
        await env.session.is_bound;
        const context = {
            isMobile: config.device.isMobile,
            ...env.session.user_context
        };
        const data = await env.rpc({
            route: '/mail/init_messaging',
            params: { context: context }
        });
        dispatch('_initMessaging', data);
        env.call('bus_service', 'onNotification', null, notifs =>
            dispatch('_handleNotifications', notifs));
        env.call('bus_service', 'on', 'window_focus', null, () =>
            dispatch('_handleGlobalWindowFocus'));

        ready();
        env.call('bus_service', 'startPolling');
        dispatch('_startLoopFetchPartnerImStatus');
    },
    /**
     * Update existing thread or create a new thread
     *
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} param1._model
     * @param {integer} param1.id
     * @param {...Object} param1.kwargs
     * @return {string} thread local Id
     */
    insertThread(
        { dispatch, getters, state },
        {
            _model,
            id,
            ...kwargs
        }
    ) {
        let thread = getters.thread({
            _model,
            id,
        });
        if (!thread) {
            const threadLocalId = dispatch('_createThread', {
                _model,
                id,
                ...kwargs,
            });
            thread = state.threads[threadLocalId];
        } else {
            Object.assign(thread, kwargs); // aku todo
        }
        return thread.localId;
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {integer} channelId
     * @param {Object} param2
     * @param {boolean} [param2.autoselect=false]
     */
    async joinChannel(
        { dispatch, env, state },
        channelId,
        { autoselect=false }={}
    ) {
        const channel = state.threads[`mail.channel_${channelId}`];
        if (channel) {
            return;
        }
        const data = await env.rpc({
            model: 'mail.channel',
            method: 'channel_join_and_get_info',
            args: [[channelId]]
        });
        const threadLocalId = dispatch('_createThread', { ...data });
        if (state.threads[threadLocalId].is_minimized){
            dispatch('openThread', threadLocalId, {
                chatWindowMode: 'last',
            });
        }
        if (autoselect) {
            dispatch('openThread', threadLocalId, {
                resetDiscussDomain: true,
            });
        }
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {string} composerId
     * @param {string} attachmentLocalId
     */
    linkAttachmentToComposer({ dispatch, state }, composerId, attachmentLocalId) {
        const composerAttachmentLocalIds = state.composers[composerId].attachmentLocalIds;
        if (composerAttachmentLocalIds.includes(attachmentLocalId)) {
            return;
        }
        dispatch('_updateComposer', composerId, {
            attachmentLocalIds: composerAttachmentLocalIds.concat([attachmentLocalId]),
        });
        const attachment = state.attachments[attachmentLocalId];
        if (attachment.composerId === composerId) {
            return;
        }
        dispatch('_updateAttachment', attachmentLocalId, {
            composerId,
        });
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {string} threadLocalId
     * @param {Object} [param2={}]
     * @param {Array} [param2.searchDomain=[]]
     */
    async loadMoreMessagesOnThread(
        { dispatch, env, state },
        threadLocalId,
        { searchDomain=[] }={}
    ) {
        const stringifiedDomain = JSON.stringify(searchDomain);
        const thread = state.threads[threadLocalId];
        const threadCacheLocalId = thread.cacheLocalIds[stringifiedDomain];
        const threadCache = state.threadCaches[threadCacheLocalId];
        let domain = searchDomain.length ? searchDomain : [];
        domain = dispatch('_extendMessageDomainWithThreadDomain', {
            domain,
            threadLocalId,
        });
        if (
            threadCache.isAllHistoryLoaded &&
            threadCache.isLoadingMore
        ) {
            return;
        }
        threadCache.isLoadingMore = true;
        const minMessageId = Math.min(
            ...threadCache.messageLocalIds.map(messageLocalId =>
                state.messages[messageLocalId].id)
        );
        domain = [['id', '<', minMessageId]].concat(domain);
        const messagesData = await env.rpc({
            model: 'mail.message',
            method: 'message_fetch',
            args: [domain],
            kwargs: dispatch('_getThreadFetchMessagesKwargs', threadLocalId),
        }, { shadow: true });
        dispatch('_handleThreadLoaded', threadLocalId, {
            messagesData,
            searchDomain,
        });
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {string} threadLocalId
     * @param {Object} [param2={}]
     * @param {Array} [params2.searchDomain=[]]
     */
    async loadThreadCache(
        { dispatch },
        threadLocalId,
        { searchDomain=[] }={}
    ) {
        dispatch('_loadMessagesOnThread', threadLocalId, { searchDomain });
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {string[]} threadLocalIds
     */
    async loadThreadPreviews({ dispatch, env, state }, threadLocalIds) {
        const threads = threadLocalIds.map(localId => state.threads[localId]);
        const channelIds = threads.reduce((list, thread) => {
            if (thread._model === 'mail.channel') {
                return list.concat(thread.id);
            }
            return list;
        }, []);
        const messagePreviews = await env.rpc({
            model: 'mail.channel',
            method: 'channel_fetch_preview',
            args: [channelIds],
        }, { shadow: true });
        for (const preview of messagePreviews) {
            dispatch('_insertMessage', preview.last_message);
        }
    },
    /**
     * @param {Object} param0
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {Array[]} domains
     */
    async markAllMessagesAsRead({ env, state }, domain) {
        await env.rpc({
            model: 'mail.message',
            method: 'mark_all_as_read',
            kwargs: {
                channel_ids: [],
                domain
            }
        });
        if (state.discuss.isOpen) {
            state.discuss.inboxMarkAsReadCounter++;
        }
    },
    /**
     * @param {Object} param0
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string[]} param1.messageLocalIds
     */
    async markMessagesAsRead({ env, state }, messageLocalIds) {
        const messageIds = messageLocalIds
            .filter(localId => {
                const message = state.messages[localId];
                // If too many messages, not all are fetched,
                // and some might not be found
                return !message || message.threadLocalIds.includes('mail.box_inbox');
            })
            .map(localId => state.messages[localId].id);
        if (!messageIds.length) {
            return;
        }
        await env.rpc({
            model: 'mail.message',
            method: 'set_message_done',
            args: [messageIds]
        });
    },
    /**
     * @param {Object} param0
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {string} threadLocalId
     */
    async markThreadAsSeen({ env, state }, threadLocalId) {
        const thread = state.threads[threadLocalId];
        if (thread.message_unread_counter === 0) {
            return;
        }
        if (thread._model === 'mail.channel') {
            const seen_message_id = await env.rpc({
                model: 'mail.channel',
                method: 'channel_seen',
                args: [[thread.id]]
            }, { shadow: true });
            thread.seen_message_id = seen_message_id;
        }
        thread.message_unread_counter = 0;
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param1
     * @param {integer} param1.id
     * @param {string} param1.model
     */
    openDocument({ dispatch, env }, { id, model }) {
        env.do_action({
            type: 'ir.actions.act_window',
            res_model: model,
            views: [[false, 'form']],
            res_id: id,
        });
        dispatch('closeMessagingMenu');
        dispatch('closeAllChatWindows');
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {string} threadLocalId
     * @param {Object} param2
     * @param {string} [param2.chatWindowMode]
     * @param {boolean} [param2.resetDiscussDomain=false]
     */
    openThread(
        { dispatch, state },
        threadLocalId,
        {
            chatWindowMode,
            resetDiscussDomain=false
        }={}
    ) {
        if (
            (
                !state.isMobile &&
                state.discuss.isOpen
            ) ||
            (
                state.isMobile &&
                state.threads[threadLocalId]._model === 'mail.box'
            )
        ) {
            if (resetDiscussDomain) {
                dispatch('updateDiscuss', {
                    domain: [],
                });
            }
            dispatch('updateDiscuss', {
                activeThreadLocalId: threadLocalId,
            });
        } else {
            dispatch('_openChatWindow', threadLocalId, {
                mode: chatWindowMode,
            });
        }
        if (!state.isMobile) {
            dispatch('closeMessagingMenu');
        }
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.getters
     * @param {Object} param0.state
     * @param {string} threadLocalId
     * @param {Object} data
     * @param {string[]} data.attachmentLocalIds
     * @param {*[]} data.canned_response_ids
     * @param {integer[]} data.channel_ids
     * @param {string} data.htmlContent
     * @param {boolean} [data.isLog=false]
     * @param {string} data.subject
     * @param {string} [data.subtype='mail.mt_comment']
     * @param {integer} [data.subtype_id]
     * @param {String} [data.threadCacheLocalId]
     * @param {Object} [options]
     * @param {integer} options.res_id
     * @param {string} options.res_model
     */
    async postMessageOnThread(
        { dispatch, env, getters, state },
        threadLocalId,
        data,
        options
    ) {
        const thread = state.threads[threadLocalId];
        if (thread._model === 'mail.box') {
            const {
                res_id,
                res_model,
            } = options;
            const otherThread = getters.thread({
                _model: res_model,
                id: res_id,
            });
            return dispatch('postMessageOnThread', otherThread.localId, {
                ...data,
                threadLocalId,
            });
        }
        const {
            attachmentLocalIds,
            canned_response_ids,
            channel_ids=[],
            context,
            htmlContent,
            isLog=false,
            subject,
            // subtype='mail.mt_comment',
            subtype_id,
            threadCacheLocalId,
        } = data;
        let body = htmlContent.replace(/&nbsp;/g, ' ').trim();
        // This message will be received from the mail composer as html content
        // subtype but the urls will not be linkified. If the mail composer
        // takes the responsibility to linkify the urls we end up with double
        // linkification a bit everywhere. Ideally we want to keep the content
        // as text internally and only make html enrichment at display time but
        // the current design makes this quite hard to do.
        body = mailUtils.parseAndTransform(body, mailUtils.addLink);
        body = dispatch('_generateEmojisOnHtml', body);
        let postData = {
            attachment_ids: attachmentLocalIds.map(localId =>
                    state.attachments[localId].id),
            body,
            partner_ids: dispatch('_getMentionedPartnerIdsFromHtml', body),
            message_type: 'comment',
        };
        if (thread._model === 'mail.channel') {
            const command = dispatch('_getCommandFromText', body);
            Object.assign(postData, {
                command,
                subtype: 'mail.mt_comment'
            });
            await env.rpc({
                model: 'mail.channel',
                method: command ? 'execute_command' : 'message_post',
                args: [thread.id],
                kwargs: postData
            });
        } else {
            Object.assign(postData, {
                channel_ids: channel_ids.map(channelId => [4, channelId, false]),
                canned_response_ids
            });
            if (subject) {
                postData.subject = subject;
            }
            Object.assign(postData, {
                context,
                subtype: isLog ? 'mail.mt_note' : 'mail.mt_comment',
                subtype_id
            });
            const id = await env.rpc({
                model: thread._model,
                method: 'message_post',
                args: [thread.id],
                kwargs: postData
            });
            const [messageData] = await env.rpc({
                model: 'mail.message',
                method: 'message_format',
                args: [[id]]
            });
            dispatch('_createMessage', {
                ...messageData,
                model: thread._model,
                res_id: thread.id
            });
        }
        if (threadCacheLocalId) {
            const threadCache = state.threadCaches[threadCacheLocalId];
            threadCache.currentPartnerMessagePostCounter++;
        }
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.getters
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {Event} param1.ev
     * @param {integer} param1.id
     * @param {string} param1.model
     */
    async redirect(
        { dispatch, env, getters, state },
        { ev, id, model }
    ) {
        if (model === 'mail.channel') {
            ev.stopPropagation();
            const channel = getters.thread({
                _model: 'mail.channel',
                id,
            });
            if (!channel) {
                dispatch('joinChannel', id, {
                    autoselect: true,
                });
                return;
            }
            dispatch('openThread', channel.localId);
        } else if (model === 'res.partner') {
            if (id === env.session.partner_id) {
                dispatch('openDocument', {
                    model: 'res.partner',
                    id,
                });
                return;
            }
            const partnerLocalId = `res.partner_${id}`;
            let partner = state.partners[partnerLocalId];
            if (!partner) {
                dispatch('_insertPartner', { id });
                partner = state.partners[partnerLocalId];
            }
            if (partner.userId === undefined) {
                // rpc to check that
                await dispatch('_checkPartnerIsUser', partnerLocalId);
            }
            if (partner.userId === null) {
                // partner is not a user, open document instead
                dispatch('openDocument', {
                    model: 'res.partner',
                    id: partner.id,
                });
                return;
            }
            ev.stopPropagation();
            const chat = getters.chatFromPartner(`res.partner_${id}`);
            if (!chat) {
                dispatch('createChannel', {
                    autoselect: true,
                    partnerId: id,
                    type: 'chat',
                });
                return;
            }
            dispatch('openThread', chat.localId);
        } else {
            dispatch('openDocument', {
                model: 'res.partner',
                id,
            });
        }
    },
    /**
     * @param {Object} param0
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {string} threadLocalId
     * @param {string} newName
     */
    async renameThread({ env, state }, threadLocalId, newName) {
        const thread = state.threads[threadLocalId];
        if (thread.channel_type === 'chat') {
            await env.rpc({
                model: 'mail.channel',
                method: 'channel_set_custom_name',
                args: [thread.id],
                kwargs: {
                    name: newName,
                }
            });
        }
        thread.custom_channel_name = newName;
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {string} oldChatWindowLocalId chat window to replace
     * @param {string} newChatWindowLocalId chat window to replace with
     */
    replaceChatWindow(
        { dispatch },
        oldChatWindowLocalId,
        newChatWindowLocalId,
    ) {
        dispatch('_swapChatWindows', newChatWindowLocalId, oldChatWindowLocalId);
        dispatch('closeChatWindow', oldChatWindowLocalId);
        dispatch('focusChatWindow', newChatWindowLocalId);
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} chatWindowStates format:
     *
     *   {
     *      [chatWindowLocalId]: {
     *         composerAttachmentLocalIds: {Array},
     *         composerTextInputHtmlContent: {String},
     *         scrollTop: {integer}
     *      },
     *   }
     */
    saveChatWindowsStates({ dispatch }, chatWindowStates) {
        dispatch('_updateChatWindowManager', { storedChatWindowStates: chatWindowStates });
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {function} param1.callback
     * @param {string} param1.keyword
     * @param {integer} [param1.limit=10]
     */
    async searchPartners(
        { dispatch, env, state },
        { callback, keyword, limit=10 }
    ) {
        // prefetched partners
        let partners = [];
        const searchRegexp = new RegExp(
            _.str.escapeRegExp(utils.unaccent(keyword)),
            'i'
        );
        const currentPartner = state.partners[state.currentPartnerLocalId];
        for (const partner of Object.values(state.partners)) {
            if (partners.length < limit) {
                if (
                    partner.id !== currentPartner.id &&
                    searchRegexp.test(partner.name)
                ) {
                    partners.push(partner);
                }
            }
        }
        if (!partners.length) {
            const partnersData = await env.rpc(
                {
                    model: 'res.partner',
                    method: 'im_search',
                    args: [keyword, limit]
                },
                { shadow: true }
            );
            for (const data of partnersData) {
                const partnerLocalId = dispatch('_insertPartner', data);
                partners.push(state.partners[partnerLocalId]);
            }
        }
        callback(partners);
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Number} notifiedAutofocusCounter
     */
    setChatWindowManagerNotifiedAutofocusCounter({ dispatch }, notifiedAutofocusCounter) {
        dispatch('_updateChatWindowManager', { notifiedAutofocusCounter });
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} chatWindowLocalId either 'new_message' or thread local Id
     */
    shiftLeftChatWindow({ dispatch, state }, chatWindowLocalId) {
        const cwm = state.chatWindowManager;
        const index = cwm.chatWindowLocalIds.findIndex(localId =>
            localId === chatWindowLocalId);
        if (index === cwm.chatWindowLocalIds.length-1) {
            // already left-most
            return;
        }
        const otherChatWindowLocalId = cwm.chatWindowLocalIds[index+1];
        cwm.chatWindowLocalIds[index] = otherChatWindowLocalId;
        cwm.chatWindowLocalIds[index+1] = chatWindowLocalId;
        dispatch('_computeChatWindows');
        dispatch('focusChatWindow', chatWindowLocalId);
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {string} chatWindowLocalId either 'new_message' or thread local Id
     */
    shiftRightChatWindow({ dispatch, state }, chatWindowLocalId) {
        const cwm = state.chatWindowManager;
        const index = cwm.chatWindowLocalIds.findIndex(localId =>
            localId === chatWindowLocalId);
        if (index === 0) {
            // already right-most
            return;
        }
        const otherChatWindowLocalId = cwm.chatWindowLocalIds[index-1];
        cwm.chatWindowLocalIds[index] = otherChatWindowLocalId;
        cwm.chatWindowLocalIds[index-1] = chatWindowLocalId;
        dispatch('_computeChatWindows');
        dispatch('focusChatWindow', chatWindowLocalId);
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {string} threadLocalId
     */
    toggleFoldThread({ dispatch, state }, threadLocalId) {
        const thread = state.threads[threadLocalId];
        Object.assign(thread, {
            is_minimized: true,
            state: thread.state === 'open' ? 'folded' : 'open',
        });
        dispatch('_notifyServerThreadState', threadLocalId);
        if (thread.state === 'open') {
            dispatch('focusChatWindow', threadLocalId);
        }
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     */
    toggleMessagingMenuMobileNewMessage({ dispatch, state }) {
        dispatch('updateMessagingMenu', {
            isMobileNewMessageToggled: !state.messagingMenu.isMobileNewMessageToggled,
        });
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     */
    toggleMessagingMenuOpen({ dispatch, state }) {
        dispatch('updateMessagingMenu', {
            isOpen: !state.messagingMenu.isOpen,
        });
    },
    /**
     * @param {Object} param0
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {string} messageLocalId
     */
    async toggleStarMessage({ env, state }, messageLocalId) {
        return env.rpc({
            model: 'mail.message',
            method: 'toggle_message_starred',
            args: [[state.messages[messageLocalId].id]]
        });
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {string} attachmentLocalId
     */
    async unlinkAttachment({ dispatch, env, state }, attachmentLocalId) {
        const attachment = state.attachments[attachmentLocalId];
        await env.rpc({
            model: 'ir.attachment',
            method: 'unlink',
            args: [attachment.id],
        }, { shadow: true });
        dispatch('deleteAttachment', attachmentLocalId);
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {string} composerId
     */
    unlinkAttachmentsFromComposer({ dispatch, state }, composerId) {
        const attachmentLocalIds = state.composers[composerId].attachmentLocalIds;
        dispatch('_updateComposer', composerId, {
            attachmentLocalIds: [],
        });
        for (const attachmentLocalId of attachmentLocalIds) {
            const attachment = state.attachments[attachmentLocalId];
            if (!attachment.composerId === composerId) {
                return;
            }
            dispatch('_updateAttachment', attachmentLocalId, {
                composerId: null,
            });
        }
    },
    /**
     * @param {Object} param0
     * @param {Object} param0.env
     */
    async unstarAllMessages({ env }) {
        return env.rpc({
            model: 'mail.message',
            method: 'unstar_all',
        });
    },
    /**
     * @param {Object} param0
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {string} channelLocalId
     */
    async unsubscribeFromChannel({ env, state }, channelLocalId) {
        const channel = state.threads[channelLocalId];
        if (channel.channel_type === 'channel') {
            return env.rpc({
                model: 'mail.channel',
                method: 'action_unfollow',
                args: [[channel.id]]
            });
        }
        return env.rpc({
            model: 'mail.channel',
            method: 'channel_pin',
            args: [channel.uuid, false]
        });
    },
    /**
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {string} id
     * @param {any} changes
     */
    updateDialogInfo({ state }, id, changes) {
        const dialog  = state.dialogManager.dialogs.find(dialog => dialog.id === id);
        if (!dialog) {
            return;
        }
        Object.assign(dialog.info, changes);
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} changes
     * @param {string} [changes.activeMobileNavbarTabId]
     * @param {string} [changes.activeThreadLocalId]
     * @param {Array} [changes.domain]
     * @param {string} [changes.targetThreadLocalId]
     */
    updateDiscuss({ dispatch, state }, changes) {
        let toApplyChanges = { ...changes };
        const wasDiscussOpen = state.discuss.isOpen;
        if (
            'activeMobileNavbarTabId' in changes &&
            changes.activeMobileNavbarTabId === 'mailbox'
        ) {
            toApplyChanges.activethreadLocalId = 'mail.box_inbox';
        }
        if (
            'activeThreadLocalId' in changes &&
            !('targetThreadLocalId' in changes)
        ) {
            Object.assign(toApplyChanges, {
                targetLocalId: changes.activeThreadLocaLId,
                targetThreadCounter: state.discuss.targetThreadCounter + 1,
            });
        }
        if ('targetThreadLocalId' in changes) {
            toApplyChanges.targetThreadCounter = state.discuss.targetThreadCounter + 1;
        }
        if ('domain' in changes) {
            toApplyChanges.stringifiedDomain = JSON.stringify(state.discuss.domain);
        }
        Object.assign(state.discuss, toApplyChanges);
        if (wasDiscussOpen !== state.discuss.isOpen) {
            dispatch('_computeChatWindows');
        }
    },
    /**
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {Object} changes
     */
    updateMessagingMenu({ state }, changes) {
        Object.assign(state.messagingMenu, changes);
    },
    /**
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param1
     * @param {string|undefined} [param1.attachmentLocalId]
     * @param {string[]} param1.attachmentLocalIds
     * @return {string|undefined} unique id of open dialog, if open
     */
    viewAttachments({ dispatch }, { attachmentLocalId, attachmentLocalIds }) {
        if (!attachmentLocalIds) {
            return;
        }
        if (!attachmentLocalId) {
            attachmentLocalId = attachmentLocalIds[0];
        }
        if (!attachmentLocalIds.includes(attachmentLocalId)) {
            return;
        }
        return dispatch('_openDialog', AttachmentViewer, {
            attachmentLocalId,
            attachmentLocalIds,
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {string} partnerLocalId
     */
    async _checkPartnerIsUser({ dispatch, env, state }, partnerLocalId) {
        const partner = state.partners[partnerLocalId];
        const userIds = await env.rpc({
            model: 'res.users',
            method: 'search',
            args: [[['partner_id', '=', partner.id]]],
        });
        dispatch('_updatePartner', partnerLocalId, {
            userId: userIds.length ? userIds[0] : null,
        });
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     */
    _computeChatWindows({ state }) {
        const BETWEEN_GAP_WIDTH = 5;
        const CHAT_WINDOW_WIDTH = 325;
        const END_GAP_WIDTH = state.isMobile ? 0 : 10;
        const GLOBAL_WINDOW_WIDTH = state.globalWindow.innerWidth;
        const HIDDEN_MENU_WIDTH = 200; // max width, including width of dropup list items
        const START_GAP_WIDTH = state.isMobile ? 0 : 10;
        const cwm = state.chatWindowManager;
        const isDiscussOpen = state.discuss.isOpen;
        const chatWindowLocalIds = cwm.chatWindowLocalIds;
        let computed = {
            /**
             * Amount of visible slots available for chat windows.
             */
            availableVisibleSlots: 0,
            /**
             * Data related to the hidden menu.
             */
            hidden: {
                /**
                 * List of hidden docked chat windows. Useful to compute counter.
                 * Chat windows are ordered by their `chatWindowLocalIds` order.
                 */
                chatWindowLocalIds: [],
                /**
                 * Whether hidden menu is visible or not
                 */
                isVisible: false,
                /**
                 * Offset of hidden menu starting point from the starting point
                 * of chat window manager. Makes only sense if it is visible.
                 */
                offset: 0,
            },
            /**
             * Data related to visible chat windows. Index determine order of
             * docked chat windows.
             *
             * Value:
             *
             *  {
             *      chatWindowLocalId,
             *      offset,
             *  }
             *
             * Offset is offset of starting point of docked chat window from
             * starting point of dock chat window manager. Docked chat windows
             * are ordered by their `chatWindowLocalIds` order
             */
            visible: [],
        };
        if (!state.isMobile && isDiscussOpen) {
            cwm.computed = computed;
            return;
        }
        if (!chatWindowLocalIds.length) {
            cwm.computed = computed;
            return;
        }
        const relativeGlobalWindowWidth = GLOBAL_WINDOW_WIDTH - START_GAP_WIDTH - END_GAP_WIDTH;
        let maxAmountWithoutHidden = Math.floor(
            relativeGlobalWindowWidth / (CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH));
        let maxAmountWithHidden = Math.floor(
            (relativeGlobalWindowWidth - HIDDEN_MENU_WIDTH - BETWEEN_GAP_WIDTH) /
            (CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH));
        if (state.isMobile) {
            maxAmountWithoutHidden = 1;
            maxAmountWithHidden = 1;
        }
        if (chatWindowLocalIds.length <= maxAmountWithoutHidden) {
            // all visible
            for (let i = 0; i < chatWindowLocalIds.length; i++) {
                const chatWindowLocalId = chatWindowLocalIds[i];
                const offset = START_GAP_WIDTH + i * (CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH);
                computed.visible.push({ chatWindowLocalId, offset });
            }
            computed.availableVisibleSlots = maxAmountWithoutHidden;
        } else if (maxAmountWithHidden > 0) {
            // some visible, some hidden
            for (let i = 0; i < maxAmountWithHidden; i++) {
                const chatWindowLocalId = chatWindowLocalIds[i];
                const offset = START_GAP_WIDTH + i * ( CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH );
                computed.visible.push({ chatWindowLocalId, offset });
            }
            if (chatWindowLocalIds.length > maxAmountWithHidden) {
                computed.hidden.isVisible = !state.isMobile;
                computed.hidden.offset = computed.visible[maxAmountWithHidden-1].offset
                    + CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH;
            }
            for (let j = maxAmountWithHidden; j < chatWindowLocalIds.length; j++) {
                computed.hidden.chatWindowLocalIds.push(chatWindowLocalIds[j]);
            }
            computed.availableVisibleSlots = maxAmountWithHidden;
        } else {
            // all hidden
            computed.hidden.isVisible = !state.isMobile;
            computed.hidden.offset = START_GAP_WIDTH;
            computed.hidden.chatWindowLocalIds.concat(chatWindowLocalIds);
            console.warn('cannot display any visible chat windows (screen is too small)');
            computed.availableVisibleSlots = 0;
        }
        cwm.computed = computed;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {Object[]} [param1.attachment_ids=[]]
     * @param {string} [param1.attachment_ids[i].filename]
     * @param {integer} [param1.attachment_ids[i].id]
     * @param {boolean} [param1.attachment_ids[i].is_main]
     * @param {string} [param1.attachment_ids[i].mimetype]
     * @param {string} [param1.attachment_ids[i].name]
     * @param {Array} [param1.author_id]
     * @param {integer} [param1.author_id[0]]
     * @param {string} [param1.author_id[1]]
     * @param {string} param1.body
     * @param {integer[]} [param1.channel_ids=[]]
     * @param {Array} param1.customer_email_data
     * @param {string} param1.customer_email_status
     * @param {string} param1.date
     * @param {string} param1.email_from
     * @param {integer[]} [param1.history_partner_ids=[]]
     * @param {integer} param1.id
     * @param {boolean} [param1.isTransient=false]
     * @param {boolean} param1.is_discussion
     * @param {boolean} param1.is_note
     * @param {boolean} param1.is_notification
     * @param {string} param1.message_type
     * @param {string|boolean} [param1.model=false]
     * @param {string} param1.moderation_status
     * @param {string} param1.module_icon
     * @param {integer[]} [param1.needaction_partner_ids=[]]
     * @param {string} param1.record_name
     * @param {integer|boolean} param1.res_id
     * @param {boolean} param1.snailmail_error
     * @param {string} param1.snailmail_status
     * @param {integer[]} [param1.starred_partner_ids=[]]
     * @param {string|boolean} param1.subject
     * @param {string|boolean} param1.subtype_description
     * @param {Array} param1.subtype_id
     * @param {integer} param1.subtype_id[0]
     * @param {string} param1.subtype_id[1]
     * @param {Object[]} param1.tracking_value_ids
     * @param {*} param1.tracking_value_ids[i].changed_field
     * @param {integer} param1.tracking_value_ids[i].id
     * @param {string} param1.tracking_value_ids[i].field_type
     * @param {*} param1.tracking_value_ids[i].new_value
     * @param {*} param1.tracking_value_ids[i].old_value
     * @return {string} message local Id
     */
    _createMessage(
        { dispatch, state },
        {
            attachment_ids=[],
            author_id, author_id: [
                authorId,
                authorDisplayName
            ]=[],
            body,
            channel_ids=[],
            customer_email_data,
            customer_email_status,
            date,
            email_from,
            history_partner_ids=[],
            id,
            isTransient=false,
            is_discussion,
            is_note,
            is_notification,
            message_type,
            model,
            moderation_status,
            module_icon,
            needaction_partner_ids=[],
            record_name,
            res_id,
            snailmail_error,
            snailmail_status,
            starred_partner_ids=[],
            subject,
            subtype_description,
            subtype_id,
            tracking_value_ids,
        },
    ) {
        const messageLocalId = `mail.message_${id}`;
        if (state.messages[messageLocalId]) {
            // message already exists in store
            console.warn(`${messageLocalId} already exists in store`);
            return;
        }
        // 1. make message
        const message = {
            _model: 'mail.message',
            body,
            customer_email_data,
            customer_email_status,
            email_from,
            id,
            isTransient,
            is_discussion,
            is_note,
            is_notification,
            localId: messageLocalId,
            message_type,
            moderation_status,
            module_icon,
            snailmail_error,
            snailmail_status,
            subject,
            subtype_description,
            subtype_id,
            tracking_value_ids,
        };
        // 2. compute message links (<-- message)
        const currentPartner = state.partners[state.currentPartnerLocalId];
        let threadLocalIds = channel_ids.map(id => `mail.channel_${id}`);
        if (needaction_partner_ids.includes(currentPartner.id)) {
            threadLocalIds.push('mail.box_inbox');
        }
        if (starred_partner_ids.includes(currentPartner.id)) {
            threadLocalIds.push('mail.box_starred');
        }
        if (history_partner_ids.includes(currentPartner.id)) {
            threadLocalIds.push('mail.box_history');
        }
        if (model && res_id) {
            const originThreadLocalId = `${model}_${res_id}`;
            if (!threadLocalIds.includes(originThreadLocalId)) {
                threadLocalIds.push(originThreadLocalId);
            }
        }
        Object.assign(message, {
            attachmentLocalIds: attachment_ids.map(({ id }) => `ir.attachment_${id}`),
            authorLocalId: author_id
                ? `res.partner_${author_id[0]}`
                : undefined,
            date: date
                ? moment(time.str_to_datetime(date))
                : moment(),
            originThreadLocalId: res_id && model
                ? `${model}_${res_id}`
                : undefined,
            threadLocalIds,
        });
        state.messages[message.localId] = message;
        // 3. compute message links (--> message)
        // 3a. author: create/update + link
        if (authorId) {
            const partnerLocalId = dispatch('_insertPartner', {
                display_name: authorDisplayName,
                id: authorId,
            });
            dispatch('_linkAuthorMessageToPartner', {
                messageLocalId,
                partnerLocalId,
            });
        }
        // 3b. threads: create/update + link
        if (message.originThreadLocalId) {
            dispatch('insertThread', {
                _model: model,
                id: res_id,
            });
            if (record_name) {
                const originThread = state.threads[message.originThreadLocalId];
                originThread.name = record_name;
            }
        }
        // 3c. link message <- threads
        for (const threadLocalId of message.threadLocalIds) {
            if (!state.threads[threadLocalId]) {
                const [threadModel, threadId] = threadLocalId.split('_');
                dispatch('_createThread', {
                    _model: threadModel,
                    id: threadId,
                });
            }
            dispatch('_linkMessageToThread', {
                messageLocalId,
                threadLocalId,
            });
        }
        // 3d. attachments: create/update + link
        if (attachment_ids) {
            for (const data of attachment_ids) {
                const {
                    filename,
                    id: attachmentId,
                    is_main,
                    mimetype,
                    name,
                } = data;
                const attachmentLocalId = dispatch('_insertAttachment', {
                    filename,
                    id: attachmentId,
                    is_main,
                    mimetype,
                    name,
                });
                dispatch('_linkMessageToAttachment', {
                    attachmentLocalId,
                    messageLocalId,
                });
            }
        }
        return message.localId;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} [param1.display_name]
     * @param {string} [param1.email]
     * @param {integer} param1.id
     * @param {string} [param1.im_status]
     * @param {string} [param1.name]
     * @param {integer} [param1.userId]
     * @return {string} partner local Id
     */
    _createPartner(
        { state },
        {
            display_name,
            email,
            id,
            im_status,
            name,
            userId,
        }
    ) {
        const partner = {
            _model: 'res.partner',
            authorMessageLocalIds: [],
            display_name,
            email,
            id,
            im_status,
            localId: `res.partner_${id}`,
            name,
            userId,
        };
        const partnerLocalId = partner.localId;
        if (state.partners[partnerLocalId]) {
            // partner already exists in store
            return;
        }
        state.partners[partnerLocalId] = partner;
        // todo: links
        return partnerLocalId;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} [param1.channel_type]
     * @param {integer} [param1.counter]
     * @param {integer} [param1.create_uid]
     * @param {string|boolean} [param1.custom_channel_name]
     * @param {Object[]} [param1.direct_partner=[]]
     * @param {integer} [param1.direct_partner[0]]
     * @param {boolean} [param1.group_based_subscription]
     * @param {integer} param1.id
     * @param {boolean} [param1.isPinned=true]
     * @param {boolean} [param1.is_minimized]
     * @param {boolean} [param1.is_moderator]
     * @param {boolean} [param1.mass_mailing]
     * @param {Object} [param1.members=[]]
     * @param {string} [param1.members[i].email]
     * @param {integer} [param1.members[i].id]
     * @param {string} [param1.members[i].name]
     * @param {integer} [param1.message_needaction_counter]
     * @param {integer} [param1.message_unread_counter]
     * @param {boolean} [param1.moderation]
     * @param {string} [param1.name]
     * @param {string} [param1.public]
     * @param {integer} [param1.seen_message_id]
     * @param {Object[]} [param1.seen_partners_info]
     * @param {integer} [param1.seen_partners_info[i].fetched_message_id]
     * @param {integer} [param1.seen_partners_info[i].partner_id]
     * @param {integer} [param1.seen_partners_info[i].seen_message_id]
     * @param {string} [param1.state]
     * @param {string} [param1.uuid]
     * @param {string} [param1._model]
     * @return {string} thread local Id
     */
    _createThread(
        { dispatch, state },
        {
            channel_type,
            counter,
            create_uid,
            custom_channel_name,
            direct_partner: [directPartnerData]=[],
            group_based_subscription,
            id,
            isPinned=true,
            is_minimized,
            is_moderator,
            mass_mailing,
            members=[],
            message_needaction_counter,
            message_unread_counter,
            moderation,
            name,
            public: public2, // public is reserved keyword
            seen_message_id,
            seen_partners_info,
            state: foldState,
            uuid,
            _model,
        }
    ) {
        let _threadModel;
        if (!_model && channel_type) {
            _threadModel = 'mail.channel';
        } else {
            _threadModel = _model;
        }
        if (!_threadModel || !id) {
            throw new Error('thread must always have `model` and `id`');
        }
        const thread = {
            cacheLocalIds: [],
            channel_type,
            counter,
            create_uid,
            custom_channel_name,
            group_based_subscription,
            id,
            isPinned,
            is_minimized,
            is_moderator,
            localId: `${_threadModel}_${id}`,
            mass_mailing,
            members,
            messageLocalIds: [],
            message_needaction_counter,
            message_unread_counter,
            moderation,
            name,
            public: public2,
            seen_message_id,
            seen_partners_info,
            state: foldState,
            typingMemberLocalIds: [],
            uuid,
            _model: _threadModel,
        };
        // compute thread links (<-- thread)
        Object.assign(thread, {
            directPartnerLocalId: directPartnerData
                ? `res.partner_${directPartnerData.id}`
                : undefined,
            memberLocalIds: members.map(member => `res.partner_${member.id}`),
        });
        state.threads[thread.localId] = thread;
        // compute thread links (--> thread)
        dispatch('_createThreadCache', {
            threadLocalId: thread.localId,
        });
        /* Update thread relationships */
        if (members) {
            for (const member of members) {
                dispatch('_insertPartner', member);
            }
        }
        if (directPartnerData) {
            dispatch('_insertPartner', directPartnerData);
        }
        return thread.localId;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} [param1.stringifiedDomain='[]']
     * @param {string} param1.threadLocalId
     * @return {string} thread cache local Id
     */
    _createThreadCache(
        { state },
        { stringifiedDomain='[]', threadLocalId }
    ) {
        const threadCache = {
            currentPartnerMessagePostCounter: 0,
            isAllHistoryLoaded: false,
            isLoaded: false,
            isLoading: false,
            isLoadingMore: false,
            localId: `${threadLocalId}_${stringifiedDomain}`,
            messageLocalIds: [],
            stringifiedDomain,
            threadLocalId,
        };
        const threadCacheLocalId = threadCache.localId;
        state.threadCaches[threadCacheLocalId] = threadCache;
        if (!state.threads[threadLocalId]) {
            throw new Error('no thread exists for new thread cache');
        }
        const thread = state.threads[threadLocalId];
        if (Object.values(thread.cacheLocalIds).includes(threadCacheLocalId)) {
            return threadCacheLocalId;
        }
        thread.cacheLocalIds = {
            ...thread.cacheLocalIds,
            [stringifiedDomain]: threadCacheLocalId,
        };
        return threadCacheLocalId;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Array} param0.domain
     * @param {string} param0.threadLocalId
     * @return {Array}
     */
    _extendMessageDomainWithThreadDomain(
        { state },
        {
            domain,
            threadLocalId,
        }
    ) {
        const thread = state.threads[threadLocalId];
        if (thread._model === 'mail.channel') {
            return domain.concat([['channel_ids', 'in', [thread.id]]]);
        } else if (thread.localId === 'mail.box_inbox') {
            return domain.concat([['needaction', '=', true]]);
        } else if (thread.localId === 'mail.box_starred') {
            return domain.concat([['starred', '=', true]]);
        } else if (thread.localId === 'mail.box_history') {
            return domain.concat([['needaction', '=', false]]);
        } else if (thread.localId === 'mail.box_moderation') {
            return domain.concat([['need_moderation', '=', true]]);
        }
        return domain;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.state
     */
    async _fetchPartnerImStatus({ dispatch, env, state }) {
        let toFetchPartnersLocalIds = [];
        let partnerIdToLocalId = {};
        for (const partner of Object.values(state.partners)) {
            if (
                typeof partner.id !== 'number' || // ignore odoobot
                partner.im_status === null // already fetched and this partner has no im_status
            ) {
                continue;
            }
            toFetchPartnersLocalIds.push(partner.localId);
            partnerIdToLocalId[partner.id] = partner.localId;
        }
        if (!toFetchPartnersLocalIds.length) {
            return;
        }
        const dataList = await env.rpc({
            route: '/longpolling/im_status',
            params: {
                partner_ids: toFetchPartnersLocalIds.map(partnerLocalId =>
                    state.partners[partnerLocalId].id),
            },
        }, { shadow: true });
        for (const data of dataList) {
            dispatch('_updatePartner', `res.partner_${data.id}`, {
                im_status: data.im_status
            });
            delete partnerIdToLocalId[data.id];
        }
        // partners with no im_status => set null
        for (const noImStatusPartnerLocalId of Object.values(partnerIdToLocalId)) {
            dispatch('_updatePartner', noImStatusPartnerLocalId, {
                im_status: null,
            });
        }
    },
    /**
     * @private
     * @param {Object} unused
     * @param {Object[]} notifications
     * @return {Object[]}
     */
    _filterNotificationsOnUnsubscribe(unused, notifications) {
        const unsubscribedNotif = notifications.find(notif =>
            notif[1].info === 'unsubscribe');
        if (unsubscribedNotif) {
            notifications = notifications.filter(notif =>
                notif[0][1] !== 'mail.channel' ||
                notif[0][2] !== unsubscribedNotif[1].id);
        }
        return notifications;
    },
    /**
     * @private
     * @param {Object} unused
     * @param {string} htmlString
     * @return {string}
     */
    _generateEmojisOnHtml(unused, htmlString) {
        for (const emoji of emojis) {
            for (const source of emoji.sources) {
                const escapedSource = String(source).replace(
                    /([.*+?=^!:${}()|[\]/\\])/g,
                    '\\$1');
                const regexp = new RegExp(
                    '(\\s|^)(' + escapedSource + ')(?=\\s|$)',
                    'g');
                htmlString = htmlString.replace(regexp, '$1' + emoji.unicode);
            }
        }
        return htmlString;
    },
    /**
     * @private
     * @param {Object} unused
     * @param {string} content html content
     * @return {String|undefined} command, if any in the content
     */
    _getCommandFromText(unused, content) {
        if (content.startsWith('/')) {
            return content.substring(1).split(/\s/)[0];
        }
        return undefined;
    },
    /**
     * @private
     * @param {Object} unused
     * @param {string} content html content
     * @return {integer[]} list of mentioned partner Ids (not duplicate)
     */
    _getMentionedPartnerIdsFromHtml(unused, content) {
        const parser = new window.DOMParser();
        const node = parser.parseFromString(content, 'text/html');
        const mentions = [ ...node.querySelectorAll('.o_mention') ];
        const allPartnerIds = mentions
            .filter(mention =>
                (
                    mention.dataset.oeModel === 'res.partner' &&
                    !isNaN(Number(mention.dataset.oeId))
                ))
            .map(mention => Number(mention.dataset.oeId));
        return [ ...new Set(allPartnerIds) ];
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {string} threadLocalId
     * @return {Object}
     */
    _getThreadFetchMessagesKwargs({ env, state }, threadLocalId) {
        const thread = state.threads[threadLocalId];
        let kwargs = {
            limit: state.MESSAGE_FETCH_LIMIT,
            context: env.session.user_context
        };
        if (thread.moderation) {
            // thread is a channel
            kwargs.moderated_channel_ids = [thread.id];
        }
        return kwargs;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.env
     * @param {Object} param0.state
     */
    async _handleGlobalWindowFocus({ env, state }) {
        state.outOfFocusUnreadMessageCounter = 0;
        env.trigger_up('set_title_part', {
            part: '_chat',
        });
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} data
     * @param {integer} data.channelId
     * @param {string} [data.info]
     * @param {integer} [data.last_message_id]
     * @param {integer} [data.partner_id]
     */
    async _handleNotificationChannel({ dispatch }, data) {
        const {
            channelId,
            info,
            last_message_id,
            partner_id,
        } = data;
        switch (info) {
            case 'channel_fetched':
                return; // disabled seen notification feature
            case 'channel_seen':
                return dispatch('_handleNotificationChannelSeen', {
                    channelId,
                    last_message_id,
                    partner_id,
                });
            case 'typing_status':
                /**
                 * data.is_typing
                 * data.is_website_user
                 * data.partner_id
                 */
                return; // disabled typing status notification feature
            default:
                return dispatch('_handleNotificationChannelMessage', data);
        }
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {integer} param1.channelId
     * @param {...Object} param1.data
     * @param {Array} [param1.data.author_id]
     * @param {integer} param1.data.author_id[0]
     * @param {integer[]} param1.data.channel_ids
     */
    async _handleNotificationChannelMessage(
        { dispatch, env, state },
        { channelId, ...data }) {
        const {
            author_id: [authorPartnerId]=[],
            channel_ids,
        } = data;
        if (channel_ids.length === 1) {
            await dispatch('joinChannel', channel_ids[0]);
        }
        const messageLocalId = dispatch('_createMessage', data);
        const message = state.messages[messageLocalId];
        for (const threadLocalId of message.threadLocalIds) {
            const thread = state.threads[threadLocalId];
            if (thread._model === 'mail.channel') {
                dispatch('_linkMessageToThreadCache', {
                    messageLocalId,
                    threadCacheLocalId: thread.cacheLocalIds['[]'],
                });
            }
        }

        const currentPartner = state.partners[state.currentPartnerLocalId];
        if (authorPartnerId === currentPartner.id) {
            return;
        }

        const channelLocalId = `mail.channel_${channelId}`;
        const channel = state.threads[channelLocalId];
        const isOdooFocused = env.call('bus_service', 'isOdooFocused');
        if (!isOdooFocused) {
            dispatch('_notifyNewChannelMessageWhileOutOfFocus', {
                channelLocalId,
                messageLocalId,
            });
        }
        channel.message_unread_counter++;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.getters
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {integer} param1.channelId
     * @param {integer} param1.last_message_id
     * @param {integer} param1.partner_id
     */
    async _handleNotificationChannelSeen(
        { getters, state },
        {
            channelId,
            last_message_id,
            partner_id,
        }
    ) {

        const currentPartner = state.partners[state.currentPartnerLocalId];
        if (currentPartner.id !== partner_id) {
            return;
        }
        const channel = getters.thread({
            _model: 'mail.channel',
            id: channelId,
        });
        Object.assign(channel, {
            message_unread_counter: 0,
            seen_message_id: last_message_id,
        });
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} data
     */
    _handleNotificationNeedaction({ dispatch, state }, data) {
        const messageLocalId = dispatch('_insertMessage', data);
        const message = state.messages[messageLocalId];
        const inbox = state.threads['mail.box_inbox'];
        inbox.counter++;
        for (const threadLocalId of message.threadLocalIds) {
            const thread = state.threads[threadLocalId];
            if (
                thread.channel_type === 'channel' &&
                message.threadLocalIds.includes('mail.box_inbox')
            ) {
                thread.message_needaction_counter++;
            }
            dispatch('_linkMessageToThreadCache', {
                messageLocalId,
                threadCacheLocalId: thread.cacheLocalIds['[]'],
            });
        }
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} data
     * @param {string} [data.info]
     * @param {string} [data.type]
     */
    async _handleNotificationPartner({ dispatch }, data) {
        const {
            info,
            type,
        } = data;
        if (type === 'activity_updated') {
            /**
             * data.activity_created
             * data.activity_deleted
             */
            return; // disabled
        } else if (type === 'author') {
            /**
             * data.message
             */
            return; // disabled
        } else if (type === 'deletion') {
            /**
             * data.message_ids
             */
            return; // disabled
        } else if (type === 'mail_failure') {
            return dispatch('_handleNotificationPartnerMailFailure', data.elements);
        } else if (type === 'mark_as_read') {
            return dispatch('_handleNotificationPartnerMarkAsRead', data);
        } else if (type === 'moderator') {
            /**
             * data.message
             */
            return; // disabled
        } else if (type === 'toggle_star') {
            return dispatch('_handleNotificationPartnerToggleStar', data);
        } else if (info === 'transient_message') {
            return dispatch('_handleNotificationPartnerTransientMessage', data);
        } else if (info === 'unsubscribe') {
            return dispatch('_handleNotificationPartnerUnsubscribe', data.id);
        } else if (type === 'user_connection') {
            return dispatch('_handleNotificationPartnerUserConnection', data);
        } else {
            return dispatch('_handleNotificationPartnerChannel', data);
        }
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {Object} data
     * @param {string} data.channel_type
     * @param {integer} data.id
     * @param {string} [data.info]
     * @param {boolean} data.is_minimized
     * @param {string} data.name
     * @param {string} data.state
     * @param {string} data.uuid
     */
    _handleNotificationPartnerChannel(
        { dispatch, env, state },
        data
    ) {
        const {
            channel_type,
            id,
            info,
            is_minimized,
            name,
            state: channelState,
        } = data;
        if (channel_type !== 'channel' || channelState !== 'open') {
            return;
        }
        const thread = state.threads[`mail.channel_${id}`];
        if (
            !is_minimized &&
            info !== 'creation' &&
            (
                !thread ||
                !thread.memberLocalIds.includes(state.currentPartnerLocalId)
            )
        ) {
            env.do_notify(
                _t("Invitation"),
                _.str.sprintf(
                    _t("You have been invited to: %s"),
                    name),
            );
        }
        if (!state.threads[`mail.channel_${id}`]) {
            const threadLocalId = dispatch('_createThread', data);
            if (state.threads[threadLocalId].is_minimized){
                dispatch('openThread', threadLocalId, {
                    chatWindowMode: 'last',
                });
            }
        }
    },
    /**
     * @private
     * @param {Object} unused
     * @param {Array} elements
     */
    _handleNotificationPartnerMailFailure(unused, elements) {
        for (const data of elements) {
            // todo
        }
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.getters
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {integer[]} [param1.channel_ids=[]]
     * @param {integer[]} [param1.message_ids=[]]
     */
    _handleNotificationPartnerMarkAsRead(
        { dispatch, getters, state },
        {
            channel_ids=[],
            message_ids=[],
        }
    ) {
        const inboxLocalId = 'mail.box_inbox';
        const inbox = state.threads[inboxLocalId];
        for (const cacheLocalId of Object.values(inbox.cacheLocalIds)) {
            for (const messageId of message_ids) {
                const messageLocalId = `mail.message_${messageId}`;
                const history = state.threads['mail.box_history'];
                dispatch('_unlinkMessageFromThreadCache', {
                    messageLocalId,
                    threadCacheLocalId: cacheLocalId,
                });
                dispatch('_linkMessageToThread', {
                    messageLocalId,
                    threadLocalId: 'mail.box_history',
                });
                dispatch('_linkMessageToThreadCache', {
                    messageLocalId,
                    threadCacheLocalId: history.cacheLocalIds['[]'],
                });
            }
        }
        const mailChannelList = getters.mailChannelList();
        for (const mailChannel of mailChannelList) {
            mailChannel.message_needaction_counter = 0;
        }
        inbox.counter -= message_ids.length;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {integer[]} param1.message_ids
     * @param {boolean} param1.starred
     */
    _handleNotificationPartnerToggleStar(
        { dispatch, state },
        { message_ids=[], starred }
    ) {
        const starredBoxLocalId = 'mail.box_starred';
        const starredBox = state.threads[starredBoxLocalId];
        for (const messageId of message_ids) {
            const messageLocalId = `mail.message_${messageId}`;
            const message = state.messages[messageLocalId];
            if (!message) {
                continue;
            }
            if (starred) {
                const message = state.messages[messageLocalId];
                if (message.threadLocalIds.includes('mail.box_starred')) {
                    return;
                }
                dispatch('_linkThreadToMessage', {
                    messageLocalId,
                    threadLocalId: 'mail.box_starred',
                });
                dispatch('_linkMessageToThread', {
                    messageLocalId,
                    threadLocalId: 'mail.box_starred',
                });
                starredBox.counter++;
            } else {
                const message = state.messages[messageLocalId];
                if (!message.threadLocalIds.includes('mail.box_starred')) {
                    return;
                }
                dispatch('_unlinkThreadFromMessage', {
                    messageLocalId,
                    threadLocalId: 'mail.box_starred',
                });
                dispatch('_unlinkMessageFromThread', {
                    messageLocalId,
                    threadLocalId: 'mail.box_starred',
                });
                starredBox.counter--;
            }
        }
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {...Object} param1.kwargs
     */
    _handleNotificationPartnerTransientMessage(
        { dispatch, state },
        {
            ...kwargs
        }
    ) {
        const messageIds = Object.values(state.messages).map(message => message.id);
        const odoobot = state.partners['res.partner_odoobot'];
        dispatch('_createMessage', {
            ...kwargs,
            author_id: [odoobot.id, odoobot.name],
            id: (messageIds ? Math.max(...messageIds) : 0) + 0.01,
            isTransient: true,
        });
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {integer} channelId
     */
    _handleNotificationPartnerUnsubscribe({ dispatch, env, state }, channelId) {
        const channelLocalId = `mail.channel_${channelId}`;
        const channel = state.threads[channelLocalId];
        if (!channel) {
            return;
        }
        let message;
        if (channel.directPartnerLocalId) {
            const directPartner = state.partners[channel.directPartnerLocalId];
            message = _.str.sprintf(
                _t("You unpinned your conversation with <b>%s</b>."),
                directPartner.name);
        } else {
            message = _.str.sprintf(
                _t("You unsubscribed from <b>%s</b>."),
                channel.name);
        }
        env.do_notify(_t("Unsubscribed"), message);
        dispatch('_unpinThread', channelLocalId);
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.env
     * @param {Object} param1
     * @param {string} param1.message
     * @param {integer} param1.partner_id
     * @param {string} param1.title
     */
    _handleNotificationPartnerUserConnection(
        { dispatch, env },
        {
            message,
            partner_id,
            title,
        }
    ) {
        env.call('bus_service', 'sendNotification', title, message);
        dispatch('createChannel', {
            autoselect: true,
            partnerId: partner_id,
            type: 'chat',
        });
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object[]} notifications
     * @param {Array} notifications[i][0]
     * @param {string} notifications[i][0][0]
     * @param {string} notifications[i][0][1]
     * @param {integer} notifications[i][0][2]
     * @param {Object} notifications[i][1]
     */
    async _handleNotifications(
        { dispatch },
        notifications
    ) {
        const filteredNotifications = dispatch('_filterNotificationsOnUnsubscribe', notifications);
        const proms = filteredNotifications.map(notification => {
            const [[dbName, model, id], data] = notification;
            switch (model) {
                case 'ir.needaction':
                    return dispatch('_handleNotificationNeedaction', data);
                case 'mail.channel':
                    return dispatch('_handleNotificationChannel', {
                        channelId: id,
                        ...data
                    });
                case 'res.partner':
                    return dispatch('_handleNotificationPartner', {
                        ...data
                    });
                default:
                    console.warn(`[messaging store] Unhandled notification "${model}"`);
                    return;
            }
        });
        return Promise.all(proms);
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {string} threadLocalId
     * @param {Object} param2
     * @param {Object} param2.messageData
     * @param {Array} [param2.searchDomain=[]]
     */
    _handleThreadLoaded(
        { dispatch, state },
        threadLocalId,
        { messagesData, searchDomain=[] }
    ) {
        const stringifiedDomain = JSON.stringify(searchDomain);
        const threadCacheLocalId = dispatch('_insertThreadCache', {
            isAllHistoryLoaded: messagesData.length < state.MESSAGE_FETCH_LIMIT,
            isLoaded: true,
            isLoading: false,
            isLoadingMore: false,
            stringifiedDomain,
            threadLocalId,
        });
        for (const data of messagesData) {
            const messageLocalId = dispatch('_insertMessage', data);
            dispatch('_linkMessageToThreadCache', {
                messageLocalId,
                threadCacheLocalId,
            });
        }
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param1
     * @param {Object} param1.channel_slots
     * @param {Array} [param1.commands=[]]
     * @param {boolean} [param1.is_moderator=false]
     * @param {Object[]} [param1.mail_failures=[]]
     * @param {Object[]} [param1.mention_partner_suggestions=[]]
     * @param {Object[]} [param1.moderation_channel_ids=[]]
     * @param {integer} [param1.moderation_counter=0]
     * @param {integer} [param1.needaction_inbox_counter=0]
     * @param {Object[]} [param1.shortcodes=[]]
     * @param {integer} [param1.starred_counter=0]
     */
    _initMessaging(
        { dispatch },
        {
            channel_slots,
            commands=[],
            is_moderator=false,
            mail_failures=[],
            mention_partner_suggestions=[],
            menu_id,
            moderation_channel_ids=[],
            moderation_counter=0,
            needaction_inbox_counter=0,
            shortcodes=[],
            starred_counter=0
        }
    ) {
        dispatch('_initMessagingPartners');
        dispatch('_initMessagingChannels', channel_slots);
        dispatch('_initMessagingCommands', commands);
        dispatch('_initMessagingMailboxes', {
            is_moderator,
            moderation_counter,
            needaction_inbox_counter,
            starred_counter
        });
        dispatch('_initMessagingMailFailures', mail_failures);
        dispatch('_initMessagingCannedResponses', shortcodes);
        dispatch('_initMessagingMentionPartnerSuggestions', mention_partner_suggestions);
        dispatch('updateDiscuss', {
            menu_id,
        });
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {Object[]} shortcodes
     */
    _initMessagingCannedResponses({ state }, shortcodes) {
        const cannedResponses = shortcodes
            .map(s => {
                const { id, source, substitution } = s;
                return { id, source, substitution };
            })
            .reduce((obj, cr) => {
                obj[cr.id] = cr;
                return obj;
            }, {});
        Object.assign(state, { cannedResponses });
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param1
     * @param {Object[]} [param1.channel_channel=[]]
     * @param {Object[]} [param1.channel_direct_message=[]]
     * @param {Object[]} [param1.channel_private_group=[]]
     */
    _initMessagingChannels(
        { dispatch, state },
        {
            channel_channel=[],
            channel_direct_message=[],
            channel_private_group=[],
        }
    ) {
        for (const data of channel_channel) {
            const threadLocalId = dispatch('insertThread', {
                _model: 'mail.channel',
                ...data,
            });
            const thread = state.threads[threadLocalId];
            if (thread.is_minimized) {
                dispatch('openThread', thread.localId, {
                    chatWindowMode: 'last',
                });
            }
        }
        for (const data of channel_direct_message) {
            const threadLocalId = dispatch('insertThread', {
                _model: 'mail.channel',
                ...data,
            });
            const thread = state.threads[threadLocalId];
            if (thread.is_minimized) {
                dispatch('openThread', thread.localId, {
                    chatWindowMode: 'last',
                });
            }
        }
        for (const data of channel_private_group) {
            const threadLocalId = dispatch('insertThread', {
                _model: 'mail.channel',
                ...data,
            });
            const thread = state.threads[threadLocalId];
            if (thread.is_minimized) {
                dispatch('openThread', thread.localId, {
                    chatWindowMode: 'last',
                });
            }
        }
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {Object[]} commandsData
     */
    _initMessagingCommands({ state }, commandsData) {
        const commands = commandsData
            .map(command => {
                return {
                    id: command.name,
                    ...command
                };
            })
            .reduce((obj, command) => {
                obj[command.id] = command;
                return obj;
            }, {});
        Object.assign(state, { commands });
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param1
     * @param {boolean} param1.is_moderator
     * @param {integer} param1.moderation_counter
     * @param {integer} param1.needaction_inbox_counter
     * @param {integer} param1.starred_counter
     */
    _initMessagingMailboxes(
        { dispatch },
        {
            is_moderator,
            moderation_counter,
            needaction_inbox_counter,
            starred_counter
        }
    ) {
        dispatch('_createThread', {
            _model: 'mail.box',
            counter: needaction_inbox_counter,
            id: 'inbox',
            name: _t("Inbox"),
        });
        dispatch('_createThread', {
            _model: 'mail.box',
            counter: starred_counter,
            id: 'starred',
            name: _t("Starred"),
        });
        dispatch('_createThread', {
            _model: 'mail.box',
            id: 'history',
            name: _t("History"),
        });
        if (is_moderator) {
            dispatch('_createThread', {
                _model: 'mail.box',
                counter: moderation_counter,
                id: 'moderation',
                name: _t("Moderate Messages"),
            });
        }
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {Object[]} mailFailuresData
     */
    _initMessagingMailFailures({ state }, mailFailuresData) {
        for (const data of mailFailuresData) {
            const mailFailure = {
                ...data,
                _model: 'mail.failure',
                localId: `mail.failure_${data.message_id}`,
            };
            // /**
            //  * Get a valid object for the 'mail.preview' template
            //  *
            //  * @returns {Object}
            //  */
            // getPreview () {
            //     const preview = {
            //         body: _t("An error occured when sending an email"),
            //         date: this._lastMessageDate,
            //         documentId: this.documentId,
            //         documentModel: this.documentModel,
            //         id: 'mail_failure',
            //         imageSRC: this._moduleIcon,
            //         title: this._modelName,
            //     };
            //     return preview;
            // },
            state.mailFailures[mailFailure.localId] = mailFailure;
        }
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object[]} mentionPartnerSuggestionsData
     */
    _initMessagingMentionPartnerSuggestions(
        { dispatch },
        mentionPartnerSuggestionsData
    ) {
        for (const suggestions of mentionPartnerSuggestionsData) {
            for (const suggestion of suggestions) {
                const { email, id, name } = suggestion;
                dispatch('_insertPartner', { email, id, name });
            }
        }
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.state
     */
    _initMessagingPartners({ dispatch, env, state }) {
        dispatch('_createPartner', {
            id: 'odoobot',
            name: _t("OdooBot"),
        });
        const currentPartnerLocalId = dispatch('_createPartner', {
            display_name: env.session.partner_display_name,
            id: env.session.partner_id,
            name: env.session.name,
            userId: env.session.uid,
        });
        state.currentPartnerLocalId = currentPartnerLocalId;
    },
    /**
     * Update existing attachment or create a new attachment
     *
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {integer} param1.id
     * @param {...Object} param1.kwargs
     * @return {string} attachment local Id
     */
    _insertAttachment({ dispatch, state }, { id, ...kwargs }) {
        const attachmentLocalId = `ir.attachment_${id}`;
        if (!state.attachments[attachmentLocalId]) {
            dispatch('createAttachment', { id, ...kwargs });
        } else {
            dispatch('_updateAttachment', attachmentLocalId, kwargs);
        }
        return attachmentLocalId;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {integer} param1.id
     * @param {...Object} param1.kwargs
     * @return {string} message local Id
     */
    _insertMessage({ dispatch, state }, { id, ...kwargs }) {
        const messageLocalId = `mail.message_${id}`;
        if (!state.messages[messageLocalId]) {
            dispatch('_createMessage', { id, ...kwargs });
        } else {
            dispatch('_updateMessage', messageLocalId, kwargs);
        }
        return messageLocalId;
    },
    /**
     * Update existing partner or create a new partner
     *
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {integer} param1.id
     * @param {...Object} param1.kwargs
     * @return {string} partner local Id
     */
    _insertPartner({ dispatch, state }, { id, ...kwargs }) {
        const partnerLocalId = `res.partner_${id}`;
        if (!state.partners[partnerLocalId]) {
            dispatch('_createPartner', { id, ...kwargs });
        } else {
            dispatch('_updatePartner', partnerLocalId, kwargs);
        }
        return partnerLocalId;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} [param1.stringifiedDomain='[]']
     * @param {string} param1.threadLocalId
     * @param {...Object} param1.kwargs
     * @return {string} thread cache local Id
     */
    _insertThreadCache(
        { dispatch, state },
        {
            stringifiedDomain='[]',
            threadLocalId,
            ...kwargs
        }
    ) {
        let threadCacheLocalId;
        const thread = state.threads[threadLocalId];
        if (!thread.cacheLocalIds[stringifiedDomain]) {
            threadCacheLocalId = dispatch('_createThreadCache', {
                stringifiedDomain,
                threadLocalId,
                ...kwargs,
            });
        } else {
            threadCacheLocalId = thread.cacheLocalIds[stringifiedDomain];
            const threadCache = state.threadCaches[threadCacheLocalId];
            Object.assign(threadCache, kwargs);
        }
        return threadCacheLocalId;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} param1.messageLocalId
     * @param {string} param1.partnerLocalId
     */
    _linkAuthorMessageToPartner(
        { dispatch, state },
        { messageLocalId, partnerLocalId }
    ) {
        const partner = state.partners[partnerLocalId];
        if (partner.authorMessageLocalIds.includes(messageLocalId)) {
            return;
        }
        dispatch('_updatePartner', partnerLocalId, {
            authorMessageLocalIds: partner.authorMessageLocalIds.concat([messageLocalId])
        });
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} param1.attachmentLocalId
     * @param {string} param1.messageLocalId
     */
    _linkMessageToAttachment(
        { dispatch, state },
        {
            attachmentLocalId,
            messageLocalId,
        }
    ) {
        const attachment = state.attachments[attachmentLocalId];
        if (attachment.messageLocalIds.includes(messageLocalId)) {
            return;
        }
        dispatch('_updateAttachment', attachment.localId, {
            messageLocalIds: attachment.messageLocalIds.concat([messageLocalId]),
        });
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} param1.messageLocalId
     * @param {string} param1.threadLocalId
     */
    _linkMessageToThread(
        { dispatch, state },
        { messageLocalId, threadLocalId }
    ) {
        const thread = state.threads[threadLocalId];
        const message = state.messages[messageLocalId];
        if (thread.messageLocalIds.includes(messageLocalId)) {
            return;
        }
        // messages are ordered by id
        const index = thread.messageLocalIds.findIndex(localId => {
            const otherMessage = state.messages[localId];
            return otherMessage.id > message.id;
        });
        let newMessageLocalIds = [...thread.messageLocalIds];
        if (index !== -1) {
            newMessageLocalIds.splice(index, 0, messageLocalId);
        } else {
            newMessageLocalIds.push(messageLocalId);
        }
        thread.messageLocalIds = newMessageLocalIds;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} param1.messageLocalId
     * @param {string} param1.threadCacheLocalId
     */
    _linkMessageToThreadCache(
        { state },
        {
            messageLocalId,
            threadCacheLocalId,
        }
    ) {
        const cache = state.threadCaches[threadCacheLocalId];
        const message = state.messages[messageLocalId];
        if (cache.messageLocalIds.includes(messageLocalId)) {
            return;
        }
        // messages are ordered by id
        const index = cache.messageLocalIds.findIndex(localId => {
            const otherMessage = state.messages[localId];
            return otherMessage.id > message.id;
        });
        let newMessageLocalIds = [...cache.messageLocalIds];
        if (index !== -1) {
            newMessageLocalIds.splice(index, 0, messageLocalId);
        } else {
            newMessageLocalIds.push(messageLocalId);
        }
        const threadCache = state.threadCaches[threadCacheLocalId];
        threadCache.messageLocalIds = newMessageLocalIds;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} param1.messageLocalId
     * @param {string} param1.threadLocalId
     */
    _linkThreadToMessage(
        { state },
        { messageLocalId, threadLocalId }
    ) {
        const message = state.messages[messageLocalId];
        message.threadLocalIds.push(threadLocalId);
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {string} threadLocalId
     */
    async _loadMessagesOnDocumentThread(
        { dispatch, env, state },
        threadLocalId
    ) {
        const thread = state.threads[threadLocalId];
        if (!thread.messageIds) {
            thread.messageIds = [];
        }
        const messageIds = thread.messageIds;
        // TODO: this is for document_thread inside chat window
        // else {
        //     const [{ messageIds }] = await env.rpc({
        //         model: thread._model,
        //         method: 'read',
        //         args: [[thread.id], ['message_ids']]
        //     });
        // }
        const threadCacheLocalId = thread.cacheLocalIds['[]'];
        const threadCache = state.threadCaches[threadCacheLocalId];
        const loadedMessageIds = threadCache.messageLocalIds
            .filter(localId => messageIds.includes(state.messages[localId].id))
            .map(localId => state.messages[localId].id);
        const shouldFetch = messageIds
            .slice(0, state.MESSAGE_FETCH_LIMIT)
            .filter(messageId => !loadedMessageIds.includes(messageId))
            .length > 0;
        if (!shouldFetch) {
            return;
        }
        const idsToLoad = messageIds
            .filter(messageId => !loadedMessageIds.includes(messageId))
            .slice(0, state.MESSAGE_FETCH_LIMIT);
        threadCache.isLoading = true;
        const messagesData = await env.rpc({
            model: 'mail.message',
            method: 'message_format',
            args: [idsToLoad],
            context: env.session.user_context
        });
        dispatch('_handleThreadLoaded', threadLocalId, {
            messagesData,
        });
        // await dispatch('markMessagesAsRead', messageLocalIds);
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {string} threadLocalId
     * @param {Object} [param2]
     * @param {Array} [param2.searchDomain=[]]
     */
    async _loadMessagesOnThread(
        { dispatch, env, state },
        threadLocalId,
        { searchDomain=[] }={}
    ) {
        const thread = state.threads[threadLocalId];
        const stringifiedDomain = JSON.stringify(searchDomain);
        let threadCacheLocalId = thread.cacheLocalIds[stringifiedDomain];
        if (!threadCacheLocalId) {
            threadCacheLocalId = dispatch('_createThreadCache', {
                stringifiedDomain,
                threadLocalId,
            });
        }
        if (!['mail.box', 'mail.channel'].includes(thread._model)) {
            return dispatch('_loadMessagesOnDocumentThread', threadLocalId);
        }
        const threadCache = state.threadCaches[threadCacheLocalId];
        if (threadCache.isLoaded && threadCache.isLoading) {
            return;
        }
        let domain = searchDomain.length ? searchDomain : [];
        domain = dispatch('_extendMessageDomainWithThreadDomain', {
            domain,
            threadLocalId,
        });
        threadCache.isLoading = true;
        const messagesData = await env.rpc({
            model: 'mail.message',
            method: 'message_fetch',
            args: [domain],
            kwargs: dispatch('_getThreadFetchMessagesKwargs', threadLocalId),
        }, { shadow: true });
        dispatch('_handleThreadLoaded', threadLocalId, {
            messagesData,
            searchDomain,
        });
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     */
    _loopFetchPartnerImStatus({ dispatch }) {
        setTimeout(async () => {
            await dispatch('_fetchPartnerImStatus');
            dispatch('_loopFetchPartnerImStatus');
        }, 50*1000);
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {string} chatWindowLocalId chat Id that is invisible
     */
    _makeChatWindowVisible({ dispatch, state }, chatWindowLocalId) {
        const cwm = state.chatWindowManager;
        const {
            length: l,
            [l-1]: { chatWindowLocalId: lastVisibleChatWindowLocalId }
        } = cwm.computed.visible;
        dispatch('_swapChatWindows', chatWindowLocalId, lastVisibleChatWindowLocalId);
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {string} threadLocalId
     */
    async _minimizeThread(
        { dispatch, state },
        threadLocalId,
    ) {
        const thread = state.threads[threadLocalId];
        Object.assign(thread, {
            is_minimized: true,
            state: 'open',
        });
        dispatch('_notifyServerThreadIsMinimized', threadLocalId);
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.env
     * @param {Object} param0.getters
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} param1.channelLocalId
     * @param {string} param1.messageLocalId
     */
    _notifyNewChannelMessageWhileOutOfFocus(
        { env, getters, state },
        { channelLocalId, messageLocalId }
    ) {
        const channel = state.threads[channelLocalId];
        const message = state.messages[messageLocalId];
        const author = state.partners[message.authorLocalId];
        let notificationTitle;
        if (!author) {
            notificationTitle = _t("New message");
        } else {
            const authorName = getters.partnerName(author.localId);
            if (channel.channel_type === 'channel') {
                // hack: notification template does not support OWL components,
                // so we simply use their template to make HTML as if it comes
                // from component
                const channelIcon = env.qweb.renderToString('mail.component.ThreadIcon', {
                    storeProps: {
                        thread: channel,
                    },
                });
                const channelName = _.escape(getters.threadName(channelLocalId));
                const channelNameWithIcon = channelIcon + channelName;
                notificationTitle = _.str.sprintf(
                    _t("%s from %s"),
                    _.escape(authorName),
                    channelNameWithIcon
                );
            } else {
                notificationTitle = _.escape(authorName);
            }
        }
        const notificationContent = getters
            .messagePrettyBody(message.localId)
            .substr(0, state.PREVIEW_MSG_MAX_SIZE);
        env.call('bus_service', 'sendNotification', notificationTitle, notificationContent);
        state.outOfFocusUnreadMessageCounter++;
        const titlePattern = state.outOfFocusUnreadMessageCounter === 1
            ? _t("%d Message")
            : _t("%d Messages");
        env.trigger_up('set_title_part', {
            part: '_chat',
            title: _.str.sprintf(titlePattern, state.outOfFocusUnreadMessageCounter),
        });
    },
    /**
     * @param {Object} param0
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {string} threadLocalId
     * @return {Promise}
     */
    async _notifyServerThreadIsMinimized({ env, state }, threadLocalId) {
        const thread = state.threads[threadLocalId];
        return env.rpc({
            model: 'mail.channel',
            method: 'channel_minimize',
            args: [
                thread.uuid,
                thread.is_minimized,
            ]
        }, { shadow: true });
    },
    /**
     * @param {Object} param0
     * @param {Object} param0.env
     * @param {Object} param0.state
     * @param {string} threadLocalId
     * @return {Promise}
     */
    async _notifyServerThreadState({ env, state }, threadLocalId) {
        const thread = state.threads[threadLocalId];
        return env.rpc({
            model: 'mail.channel',
            method: 'channel_fold',
            kwargs: {
                uuid: thread.uuid,
                state: thread.state
            }
        }, { shadow: true });
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {string} chatWindowLocalId either a thread local Id or
     *   'new_message', if the chat window is already in `chatWindowLocalIds`
     *   and visible, simply focuses it. If it is already in
     *   `chatWindowLocalIds` and invisible, it swaps with last visible chat
     *   window. New chat window is added based on provided mode.
     * @param {Object} param2
     * @param {boolean} [param2.focus=true]
     * @param {string} [param2.mode='last_visible'] either 'last' or 'last_visible'
     */
    _openChatWindow(
        { dispatch, state },
        chatWindowLocalId,
        {
            focus=true,
            mode='last_visible',
        }={}
    ) {
        const cwm = state.chatWindowManager;
        if (cwm.chatWindowLocalIds.includes(chatWindowLocalId)) {
            // open already minimized chat window
            if (
                mode === 'last_visible' &&
                cwm.computed.hidden.chatWindowLocalIds.includes(chatWindowLocalId)
            ) {
                dispatch('_makeChatWindowVisible', chatWindowLocalId);
            }
        } else {
            // new chat window
            state.chatWindowManager.chatWindowLocalIds.push(chatWindowLocalId);
            if (chatWindowLocalId !== 'new_message') {
                dispatch('_minimizeThread', chatWindowLocalId);
            }
            dispatch('_computeChatWindows');
            if (mode === 'last_visible') {
                dispatch('_makeChatWindowVisible', chatWindowLocalId);
            }
        }
        if (chatWindowLocalId !== 'new_message') {
            const thread = state.threads[chatWindowLocalId];
            if (thread.state !== 'open') {
                Object.assign(thread, {
                    is_minimized: true,
                    state: 'open',
                });
                dispatch('_notifyServerThreadState', thread.localId);
            }
        }
        if (focus) {
            dispatch('focusChatWindow', chatWindowLocalId);
        }
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {owl.Component} Component
     * @param {any} info
     * @return {string} unique id of the newly open dialog
     */
    _openDialog({ state }, Component, info) {
        const id = _.uniqueId('o_Dialog');
        state.dialogManager.dialogs.push({
            Component,
            id,
            info,
        });
        return id;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {string} composerId
     * @param {string} oldAttachmentLocalId
     * @param {string} newAttachmentLocalId
     */
    _replaceAttachmentInComposer(
        { dispatch, state },
        composerId,
        oldAttachmentLocalId,
        newAttachmentLocalId
    ) {
        // change link in composer
        const composer = state.composers[composerId];
        const index = composer.attachmentLocalIds.findIndex(localId =>
            localId === oldAttachmentLocalId);
        composer.attachmentLocalIds.splice(index, 1);
        if (index >= composer.attachmentLocalIds.length) {
            composer.attachmentLocalIds.push(newAttachmentLocalId);
        } else {
            composer.attachmentLocalIds.splice(index, 0, newAttachmentLocalId);
        }
        // change link in attachments
        dispatch('_updateAttachment', oldAttachmentLocalId, {
            composerId: null,
        });
        dispatch('_updateAttachment', newAttachmentLocalId, {
            composerId,
        });
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     */
    async _startLoopFetchPartnerImStatus({ dispatch }) {
        await dispatch('_fetchPartnerImStatus');
        dispatch('_loopFetchPartnerImStatus');
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {string} chatWindowLocalId1
     * @param {string} chatWindowLocalId2
     */
    _swapChatWindows(
        { dispatch, state },
        chatWindowLocalId1,
        chatWindowLocalId2
    ) {
        const cwm = state.chatWindowManager;
        const chatWindowLocalIds = cwm.chatWindowLocalIds;
        const index1 = chatWindowLocalIds.findIndex(localId =>
            localId === chatWindowLocalId1);
        const index2 = chatWindowLocalIds.findIndex(localId =>
            localId === chatWindowLocalId2);
        if (index1 === -1 || index2 === -1) {
            return;
        }
        chatWindowLocalIds[index1] = chatWindowLocalId2;
        chatWindowLocalIds[index2] = chatWindowLocalId1;
        dispatch('_computeChatWindows');
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {string} messageLocalId
     * @param {string} attachmentLocalId
     */
    _unlinkAttachmentFromMessage({ state }, messageLocalId, attachmentLocalId) {
        const message = state.messages[messageLocalId];
        message.attachmentLocalIds = message.attachmentLocalIds.filter(localId =>
            localId !== attachmentLocalId);
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} param1.messageLocalId
     * @param {string} param1.partnerLocalId
     */
    _unlinkAuthorMessageFromPartner({ state }, {
        messageLocalId,
        partnerLocalId,
    }) {
        const partner = state.partners[partnerLocalId];
        if (!partner.authorMessageLocalIds.includes(messageLocalId)) {
            return;
        }
        partner.authorMessageLocalIds = partner.authorMessageLocalIds.filter(localId =>
            localId !== messageLocalId);
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} param1.attachmentLocalId
     * @param {strign} param1.messageLocalId
     */
    _unlinkMessageFromAttachment({ state }, {
        attachmentLocalId,
        messageLocalId,
    }) {
        const attachment = state.attachments[attachmentLocalId];
        if (!attachment.messageLocalIds.includes(messageLocalId)) {
            return;
        }
        attachment.messageLocalIds = attachment.messageLocalIds.filter(localId =>
            localId !== messageLocalId);
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} param1.messageLocalId
     * @param {string} param1.partnerLocalId
     */
    _unlinkMessageFromAuthorPartner(
        { dispatch, state },
        { messageLocalId, partnerLocalId }
    ) {
        const partner = state.partners[partnerLocalId];
        if (partner.authorMessageLocalIds.includes(messageLocalId)) {
            return;
        }
        dispatch('_updatePartner', partnerLocalId, {
            authorMessageLocalIds:
                partner.authorMessageLocalIds.filter(localId =>
                    localId !== messageLocalId),
        });
    },
    /**
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} param1.messageLocalId
     * @param {string} param1.threadLocalId
     */
    _unlinkMessageFromThread(
        { dispatch, state },
        { messageLocalId, threadLocalId }
    ) {
        const thread = state.threads[threadLocalId];
        if (!thread.messageLocalIds.includes(messageLocalId)) {
            return;
        }
        for (const threadCacheLocalId of Object.values(thread.cacheLocalIds)) {
            dispatch('_unlinkMessageFromThreadCache', {
                messageLocalId,
                threadCacheLocalId,
            });
        }
        thread.messageLocalIds = thread.messageLocalIds.filter(localId =>
            localId !== messageLocalId);
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} param1.messageLocalId
     * @param {string} param1.threadCacheLocalId
     */
    _unlinkMessageFromThreadCache(
        { state },
        { messageLocalId, threadCacheLocalId }
    ) {
        const threadCache = state.threadCaches[threadCacheLocalId];
        if (!threadCache.messageLocalIds.includes(messageLocalId)) {
            return;
        }
        threadCache.messageLocalIds = threadCache.messageLocalIds.filter(localId =>
            localId !== messageLocalId);
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} param1.messageLocalId
     * @param {string} param1.threadLocalId
     */
    _unlinkThreadFromMessage(
        { state },
        { messageLocalId, threadLocalId }
    ) {
        const message = state.messages[messageLocalId];
        message.threadLocalIds = message.threadLocalIds.filter(localId =>
            localId !== threadLocalId);
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {string} threadLocalId
     */
    _unpinThread({ state }, threadLocalId) {
        const thread = state.threads[threadLocalId];
        thread.isPinned = false;
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {string} attachmentLocalId
     * @param {Object} changes
     */
    _updateAttachment({ state }, attachmentLocalId, changes) {
        const attachment = state.attachments[attachmentLocalId];
        Object.assign(attachment, changes);
        // aku todo: compute attachment links
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {Object} changes
     */
    _updateChatWindowManager({ state }, changes) {
        Object.assign(state.chatWindowManager, changes);
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {string} composerId
     * @param {Object} changes
     */
    _updateComposer({ state }, composerId, changes) {
        const composer = state.composers[composerId];
        if (!composer) {
            throw new Error(`Cannot update non-existing composer store data for ID ${composerId}`);
        }
        for (const changeKey in changes) {
            composer[changeKey] = changes[changeKey];
        }
    },
    /**
     * AKU TODO: REDESIGN
     *
     * @private
     * @param {Object} param0
     * @param {function} param0.dispatch
     * @param {Object} param0.state
     * @param {Object} param1
     * @param {string} messageLocalId
     * @param {Object} param2
     * @param {Object[]} [param2.attachment_ids=[]]
     * @param {string} [param2.attachment_ids[i].filename]
     * @param {integer} [param2.attachment_ids[i].id]
     * @param {boolean} [param2.attachment_ids[i].is_main]
     * @param {string} [param2.attachment_ids[i].mimetype]
     * @param {string} [param2.attachment_ids[i].name]
     * @param {Array} [param2.author_id]
     * @param {integer} [param2.author_id[0]]
     * @param {string} [param2.author_id[1]]
     * @param {string} param2.body
     * @param {integer[]} [param2.channel_ids=[]]
     * @param {Array} param2.customer_email_data
     * @param {string} param2.customer_email_status
     * @param {string} param2.date
     * @param {string} param2.email_from
     * @param {integer[]} [param2.history_partner_ids=[]]
     * @param {integer} param2.id
     * @param {boolean} [param2.isTransient=false]
     * @param {boolean} param2.is_discussion
     * @param {boolean} param2.is_note
     * @param {boolean} param2.is_notification
     * @param {string} param2.message_type
     * @param {string|boolean} [param2.model=false]
     * @param {string} param2.moderation_status
     * @param {string} param2.module_icon
     * @param {integer[]} [param2.needaction_partner_ids=[]]
     * @param {string} param2.record_name
     * @param {integer|boolean} param2.res_id
     * @param {boolean} param2.snailmail_error
     * @param {string} param2.snailmail_status
     * @param {integer[]} [param2.starred_partner_ids=[]]
     * @param {string|boolean} param2.subject
     * @param {string|boolean} param2.subtype_description
     * @param {Array} param2.subtype_id
     * @param {integer} param2.subtype_id[0]
     * @param {string} param2.subtype_id[1]
     * @param {Object[]} param2.tracking_value_ids
     * @param {*} param2.tracking_value_ids[i].changed_field
     * @param {integer} param2.tracking_value_ids[i].id
     * @param {string} param2.tracking_value_ids[i].field_type
     * @param {*} param2.tracking_value_ids[i].new_value
     * @param {*} param2.tracking_value_ids[i].old_value
     */
    _updateMessage({ dispatch, state }, messageLocalId, {
        attachment_ids=[],
        author_id, author_id: [
            authorId,
            authorDisplayName
        ]=[],
        body,
        channel_ids=[],
        customer_email_data,
        customer_email_status,
        date,
        email_from,
        history_partner_ids=[],
        isTransient=false,
        is_discussion,
        is_note,
        is_notification,
        message_type,
        model,
        moderation_status,
        module_icon,
        needaction_partner_ids=[],
        record_name,
        res_id,
        snailmail_error,
        snailmail_status,
        starred_partner_ids=[],
        subject,
        subtype_description,
        subtype_id,
        tracking_value_ids,
    }) {
        const message = state.messages[messageLocalId];
        // 1. update message data
        Object.assign(message, {
            body,
            customer_email_data,
            customer_email_status,
            email_from,
            isTransient,
            is_discussion,
            is_note,
            is_notification,
            message_type,
            moderation_status,
            module_icon,
            snailmail_error,
            snailmail_status,
            subject,
            subtype_description,
            subtype_id,
            tracking_value_ids,
        });
        // 2. track old/new links
        const currentPartner = state.partners[state.currentPartnerLocalId];
        // 2.1. attachmentLocalIds
        const prevAttachmentLocalIds = message.attachmentLocalIds;
        const attachmentLocalIds = attachment_ids.map(({ id }) => `ir.attachment_${id}`);
        const oldAttachmentLocalIds = prevAttachmentLocalIds.filter(attachmentLocalId =>
            !attachmentLocalIds.includes(attachmentLocalId));
        const newAttachmentLocalIds = message.attachmentLocalIds.filter(attachmentLocalId =>
            !prevAttachmentLocalIds.includes(attachmentLocalId));
        const prevThreadLocalIds = message.threadLocalIds;
        let threadLocalIds = channel_ids.map(id => `mail.channel_${id}`);
        if (needaction_partner_ids.includes(currentPartner.id)) {
            threadLocalIds.push('mail.box_inbox');
        }
        if (starred_partner_ids.includes(currentPartner.id)) {
            threadLocalIds.push('mail.box_starred');
        }
        if (history_partner_ids.includes(currentPartner.id)) {
            threadLocalIds.push('mail.box_history');
        }
        if (model && res_id) {
            const originThreadLocalId = `${model}_${res_id}`;
            if (!threadLocalIds.includes(originThreadLocalId)) {
                threadLocalIds.push(originThreadLocalId);
            }
        }
        const oldThreadLocalIds = prevThreadLocalIds.filter(threadLocalId =>
            !threadLocalIds.includes(threadLocalId));
        const newThreadLocalIds = message.threadLocalIds.filter(threadLocalId =>
            !prevThreadLocalIds.includes(threadLocalId));
        message.threadLocalIds = threadLocalIds;
        const prevAuthorLocalId = message.authorLocalId;
        const authorLocalId = author_id
            ? `res.partner_${author_id[0]}`
            : undefined;
        // 3. re-compute message links (<-- message)
        Object.assign(message, {
            attachmentLocalIds,
            authorLocalId,
            originThreadLocalId: res_id && model
                ? `${model}_${res_id}`
                : undefined,
        });
        // 4. re-compute message links (--> message)
        // 4.1. attachmentLocalIds
        // 4.1.1. old
        for (const attachmentLocalId of oldAttachmentLocalIds) {
            dispatch('_unlinkMessageFromAttachment', {
                attachmentLocalId,
                messageLocalId,
            });
        }
        // 4.1.2. new
        for (const attachmentLocalId of newAttachmentLocalIds) {
            for (const attachmentData of attachment_ids) {
                dispatch('_insertAttachment', attachmentData);
                dispatch('_linkMessageToAttachment', {
                    attachmentLocalId,
                    messageLocalId,
                });
            }
            dispatch('_linkMessageToAttachment', {
                attachmentLocalId,
                messageLocalId,
            });
        }
        // 4.2. threadLocalIds
        // 4.2.1. old
        for (const threadLocalId of oldThreadLocalIds) {
            dispatch('_unlinkMessageFromThread', {
                messageLocalId,
                threadLocalId,
            });
        }
        // 4.2.2. new
        for (const threadLocalId of newThreadLocalIds) {
            const [threadModel, threadId] = threadLocalId.split('_');
            dispatch('insertThread', {
                _model: threadModel,
                id: threadId,
            });
            dispatch('_linkMessageToThread', {
                messageLocalId,
                threadLocalId,
            });
        }
        // 4.3. authorLocalId
        if (prevAuthorLocalId !== authorLocalId) {
            // 4.3.1. old
            if (prevAuthorLocalId) {
                dispatch('_unlinkAuthorMessageFromPartner', {
                    messageLocalId,
                    partnerLocalId: prevAuthorLocalId,
                });
            }
            // 4.3.2. new
            if (authorLocalId) {
                dispatch('_insertPartner', {
                    display_name: authorDisplayName,
                    id: authorId,
                });
                dispatch('_linkAuthorMessageToPartner', {
                    messageLocalId,
                    partnerLocalId: authorLocalId,
                });
            }
        }
        // 4.4. originThreadLocalId
        if (message.originThreadLocalId) {
            dispatch('insertThread', {
                _model: model,
                id: res_id,
            });
            if (record_name) {
                const originThread = state.threads[message.originThreadLocalId];
                originThread.record_name = record_name;
            }
        }
    },
    /**
     * @private
     * @param {Object} param0
     * @param {Object} param0.state
     * @param {string} partnerLocalId
     * @param {Object} changes
     */
    _updatePartner({ state }, partnerLocalId, changes) {
        const partner = state.partners[partnerLocalId];
        Object.assign(partner, changes);
        // todo: changes of links, e.g. messageLocalIds
    },
};

return actions;

});
