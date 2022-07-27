/** @odoo-module **/

import PublicLivechatMessage from '@im_livechat/legacy/models/public_livechat_message';

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

import { qweb } from 'web.core';
import { get_cookie, Markup, set_cookie, unaccent } from 'web.utils';

registerModel({
    name: 'LivechatButtonView',
    identifyingFields: ['publicLivechatGlobalOwner'],
    recordMethods: {
        /**
         * @param {Object} data
         * @param {Object} [options={}]
         */
        addMessage(data, options) {
            const legacyMessage = new PublicLivechatMessage(this, this.messaging, data);

            const hasAlreadyMessage = _.some(this.messaging.publicLivechatGlobal.messages, function (msg) {
                return legacyMessage.getID() === msg.id;
            });
            if (hasAlreadyMessage) {
                return;
            }
            const message = this.messaging.models['PublicLivechatMessage'].insert({
                data,
                id: data.id,
                legacyPublicLivechatMessage: legacyMessage,
            });

            if (this.messaging.publicLivechatGlobal.publicLivechat && this.messaging.publicLivechatGlobal.publicLivechat.legacyPublicLivechat) {
                this.messaging.publicLivechatGlobal.publicLivechat.legacyPublicLivechat.addMessage(legacyMessage);
            }

            if (options && options.prepend) {
                this.messaging.publicLivechatGlobal.update({
                    messages: replace([message, ...this.messaging.publicLivechatGlobal.messages]),
                });
            } else {
                this.messaging.publicLivechatGlobal.update({
                    messages: replace([...this.messaging.publicLivechatGlobal.messages, message]),
                });
            }
        },
        askFeedback() {
            this.chatWindow.legacyChatWindow.$('.o_thread_composer input').prop('disabled', true);
            this.messaging.publicLivechatGlobal.update({ feedbackView: insertAndReplace() });
            /**
             * When we enter the "ask feedback" process of the chat, we hide some elements that become
             * unnecessary and irrelevant (restart / end messages, any text field values, ...).
             */
            if (
                this.chatbot &&
                this.chatbot.currentStep &&
                this.chatbot.currentStep.data
            ) {
                this.chatbot.currentStep.data.conversation_closed = true;
                this.chatbotSaveSession();
            }
            this.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_main_restart').addClass('d-none');
            this.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_end').hide();
            this.chatWindow.legacyChatWindow.$('.o_composer_text_field')
                .removeClass('d-none')
                .val('');
        },
        /**
         * Once the script ends, adds a visual element at the end of the chat window allowing to restart
         * the whole script.
         */
        chatbotEndScript() {
            if (
                this.chatbot.currentStep &&
                this.chatbot.currentStep.data &&
                this.chatbot.currentStep.data.conversation_closed
            ) {
                // don't touch anything if the user has closed the conversation, let the chat window
                // handle the display
                return;
            }
            this.chatWindow.legacyChatWindow.$('.o_composer_text_field').addClass('d-none');
            this.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_end').show();
            this.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_restart').one('click', this.onChatbotRestartScript);
        },
        /**
         * Register current chatbot step state into localStorage to be able to resume if the visitor
         * goes to another website page or if he refreshes his page.
         *
         * (Will not work if the visitor switches browser but his livechat session will not be restored
         *  anyway in that case, since it's stored into a cookie).
         */
        chatbotSaveSession() {
            localStorage.setItem('im_livechat.chatbot.state.uuid_' + this.messaging.publicLivechatGlobal.publicLivechat.uuid, JSON.stringify({
                '_chatbot': this.chatbot.data,
                '_chatbotCurrentStep': this.chatbot.currentStep.data,
            }));
        },
        /**
         * Restart the script and then trigger the "next step" (which will be the first of the script
         * in this case).
         */
        async onChatbotRestartScript(ev) {
            this.chatWindow.legacyChatWindow.$('.o_composer_text_field').removeClass('d-none');
            this.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_end').hide();

            if (this.chatbotNextStepTimeout) {
                clearTimeout(this.chatbotNextStepTimeout);
            }

            if (this.chatbotWelcomeMessageTimeout) {
                clearTimeout(this.chatbotWelcomeMessageTimeout);
            }

            const postedMessage = await this.messaging.rpc({
                route: '/chatbot/restart',
                params: {
                    channel_uuid: this.messaging.publicLivechatGlobal.publicLivechat.uuid,
                    chatbot_script_id: this.chatbot.scriptId,
                },
            });

            if (postedMessage) {
                this.widget._chatbotAddMessage(postedMessage);
            }

            this.chatbot.update({ currentStep: clear() });
            this.chatbotSetIsTyping();
            this.update({
                chatbotNextStepTimeout: setTimeout(
                    this.widget._chatbotTriggerNextStep.bind(this.widget),
                    this.chatbot.messageDelay,
                ),
            });
        },
        /**
         * See 'chatbotSaveSession'.
         *
         * We retrieve the livechat uuid from the session cookie since the livechat Widget is not yet
         * initialized when we restore the chatbot state.
         *
         * We also clear any older keys that store a previously saved chatbot session.
         * (In that case we clear the actual browser's local storage, we don't use the localStorage
         * object as it does not allow browsing existing keys, see 'local_storage.js'.)
         */
        chatbotRestoreSession() {
            const browserLocalStorage = window.localStorage;
            if (browserLocalStorage && browserLocalStorage.length) {
                for (let i = 0; i < browserLocalStorage.length; i++) {
                    const key = browserLocalStorage.key(i);
                    if (key.startsWith('im_livechat.chatbot.state.uuid_') && key !== this.chatbotSessionCookieKey) {
                        browserLocalStorage.removeItem(key);
                    }
                }
            }
            const chatbotState = localStorage.getItem(this.chatbotSessionCookieKey);
            if (chatbotState) {
                this.chatbot.update({ currentStep: insertAndReplace({ data: this.localStorageChatbotState._chatbotCurrentStep }) });
            }
        },
        closeChat() {
            this.update({ chatWindow: clear() });
            set_cookie('im_livechat_session', "", -1); // remove cookie
        },
        /**
         * Called when the visitor leaves the livechat chatter the first time (first click on X button)
         * this will deactivate the mail_channel, notify operator that visitor has left the channel.
         */
        leaveSession() {
            const cookie = get_cookie('im_livechat_session');
            if (cookie) {
                const channel = JSON.parse(cookie);
                this.messaging.rpc({ route: '/im_livechat/visitor_leave_session', params: { uuid: channel.uuid } });
                set_cookie('im_livechat_session', "", -1); // remove cookie
            }
        },
        openChat() {
            if (this.isOpenChatDebounced) {
                this.openChatDebounced();
            } else {
                this._openChat();
            }
        },
        async openChatWindow() {
            this.update({ chatWindow: insertAndReplace() });
            await this.chatWindow.legacyChatWindow.appendTo($('body'));
            const cssProps = { bottom: 0 };
            cssProps[this.messaging.locale.textDirection === 'rtl' ? 'left' : 'right'] = 0;
            this.chatWindow.legacyChatWindow.$el.css(cssProps);
            this.widget.$el.hide();
            this._openChatWindowChatbot();
        },
        /**
         * Adds a small "is typing" animation into the chat window.
         *
         * @param {boolean} [isWelcomeMessage=false]
         */
        chatbotSetIsTyping(isWelcomeMessage = false) {
            if (this.isTypingTimeout) {
                clearTimeout(this.isTypingTimeout);
            }
            this.widget._chatbotDisableInput('');
            this.update({
                isTypingTimeout: setTimeout(
                    () => {
                        this.chatWindow.legacyChatWindow.$('.o_mail_thread_content').append(
                            $(qweb.render('im_livechat.legacy.chatbot.is_typing_message', {
                                'chatbotImageSrc': `/im_livechat/operator/${
                                    this.messaging.publicLivechatGlobal.publicLivechat.operator.id
                                }/avatar`,
                                'chatbotName': this.chatbot.name,
                                'isWelcomeMessage': isWelcomeMessage,
                            }))
                        );
                        this.chatWindow.publicLivechatView.widget.scrollToBottom();
                    },
                    this.chatbot.messageDelay / 3,
                ),
            });
        },
        /**
         * @param {Object} message
         */
        async sendMessage(message) {
            await this._sendMessageChatbotBefore();
            await this._sendMessage(message);
            this._sendMessageChatbotAfter();
        },
        async willStart() {
            try {
                await this._willStart();
            } finally {
                await this._willStartChatbot();
            }
        },
        /**
         * @private
         * @returns {string}
         */
        _computeButtonBackgroundColor() {
            return this.messaging.publicLivechatGlobal.options.button_background_color;
        },
        /**
         * @returns {string}
         */
        _computeButtonText() {
            if (this.messaging.publicLivechatGlobal.options.button_text) {
                return this.messaging.publicLivechatGlobal.options.button_text;
            }
            return this.env._t("Chat with one of our collaborators");
        },
        /**
         * @returns {string}
         */
        _computeButtonTextColor() {
            return this.messaging.publicLivechatGlobal.options.button_text_color;
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeChannelId() {
            return this.messaging.publicLivechatGlobal.options.channel_id;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChatbot() {
            if (this.isTestChatbot) {
                return insertAndReplace({ data: this.testChatbotData.chatbot });
            }
            if (this.chatbotState === 'init') {
                return insertAndReplace({ data: this.rule.chatbot });
            }
            if (this.chatbotState === 'welcome') {
                return insertAndReplace({ data: this.livechatInit.rule.chatbot });
            }
            if (this.chatbotState === 'restore_session' && this.localStorageChatbotState) {
                return insertAndReplace({ data: this.localStorageChatbotState._chatbot });
            }
            return clear();
        },
        /**
         * @private
         * @returns {integer|FieldCommand}
         */
        _computeChatbotMessageDelay() {
            if (this.isWebsiteLivechatChatbotFlow) {
                return 100;
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeChatbotState() {
            if (this.rule && !!this.rule.chatbot) {
                return 'init';
            }
            if (this.livechatInit && this.livechatInit.rule.chatbot) {
                return 'welcome';
            }
            return clear();
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeCurrentPartnerId() {
            if (!this.messaging.publicLivechatGlobal.isAvailable) {
                return clear();
            }
            return this.messaging.publicLivechatGlobal.options.current_partner_id;
        },
        /**
        * @private
        * @returns {string}
        */
        _computeDefaultMessage() {
            if (this.messaging.publicLivechatGlobal.options.default_message) {
                return this.messaging.publicLivechatGlobal.options.default_message;
            }
            return this.env._t("How may I help you?");
        },
        /**
         * @private
         * @returns {string}
         */
        _computeDefaultUsername() {
            if (this.messaging.publicLivechatGlobal.options.default_username) {
                return this.messaging.publicLivechatGlobal.options.default_username;
            }
            return this.env._t("Visitor");
        },
        /**
         * @private
         * @returns {string}
         */
        _computeHeaderBackgroundColor() {
            return this.messaging.publicLivechatGlobal.options.header_background_color;
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeInputPlaceholder() {
            if (this.isChatbot) {
                // void the default livechat placeholder in the user input
                // as we use it for specific things (e.g: showing "please select an option above")
                return clear();
            }
            if (this.messaging.publicLivechatGlobal.options.input_placeholder) {
                return this.messaging.publicLivechatGlobal.options.input_placeholder;
            }
            return this.env._t("Ask something ...");
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsChatbot() {
            if (this.isTestChatbot) {
                return true;
            }
            if (this.rule && this.rule.chatbot) {
                return true;
            }
            if (this.livechatInit && this.livechatInit.rule.chatbot) {
                return true;
            }
            if (this.chatbotState === 'welcome') {
                return true;
            }
            if (this.localStorageChatbotState) {
                return true;
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeIsOpenChatDebounced() {
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeLocalStorageChatbotState() {
            if (!this.sessionCookie) {
                return clear();
            }
            const data = localStorage.getItem(this.chatbotSessionCookieKey);
            if (!data) {
                return clear();
            }
            return JSON.parse(data);
        },
        /**
         * @private
         * @returns {_.debounce}
         */
        _computeOpenChatDebounced() {
            return _.debounce(this._openChat, 200, true);
        },
        /**
         * @private
         * @returns {string}
         */
        _computeServerUrl() {
            if (this.isChatbot) {
                return this.messaging.publicLivechatGlobal.chatbotServerUrl;
            }
            return this.messaging.publicLivechatGlobal.serverUrl;
        },
        /**
         * @returns {string|FieldCommand}
         */
        _computeChatbotSessionCookieKey() {
            if (!this.sessionCookie) {
                return clear();
            }
            return 'im_livechat.chatbot.state.uuid_' + JSON.parse(this.sessionCookie).uuid;
        },
        /**
         * @private
         * @returns {string}
         */
        _computeTitleColor() {
            return this.messaging.publicLivechatGlobal.options.title_color;
        },
        /**
         * @private
         */
        _openChat() {
            if (this.isOpeningChat) {
                return;
            }
            const cookie = get_cookie('im_livechat_session');
            let def;
            this.update({ isOpeningChat: true });
            clearTimeout(this.autoOpenChatTimeout);
            if (cookie) {
                def = Promise.resolve(JSON.parse(cookie));
            } else {
                // re-initialize messages cache
                this.messaging.publicLivechatGlobal.update({ messages: clear() });
                def = this.messaging.rpc({
                    route: '/im_livechat/get_session',
                    params: this.widget._prepareGetSessionParameters(),
                }, { silent: true });
            }
            def.then((livechatData) => {
                if (!livechatData || !livechatData.operator_pid) {
                    try {
                        this.widget.displayNotification({
                            message: this.env._t("No available collaborator, please try again later."),
                            sticky: true,
                        });
                    } catch (_err) {
                        /**
                         * Failure in displaying notification happens when
                         * notification service doesn't exist, which is the case in
                         * external lib. We don't want notifications in external
                         * lib at the moment because they use bootstrap toast and
                         * we don't want to include boostrap in external lib.
                         */
                        console.warn(this.env._t("No available collaborator, please try again later."));
                    }
                } else {
                    this.messaging.publicLivechatGlobal.update({
                        publicLivechat: insertAndReplace({ data: livechatData }),
                    });
                    return this.openChatWindow().then(() => {
                        if (!this.history) {
                            this.widget._sendWelcomeMessage();
                        }
                        this.widget._renderMessages();
                        this.messaging.publicLivechatGlobal.update({ notificationHandler: insertAndReplace() });

                        set_cookie('im_livechat_session', unaccent(JSON.stringify(this.messaging.publicLivechatGlobal.publicLivechat.legacyPublicLivechat.toData()), true), 60 * 60);
                        set_cookie('im_livechat_auto_popup', JSON.stringify(false), 60 * 60);
                        if (this.messaging.publicLivechatGlobal.publicLivechat.operator) {
                            const operatorPidId = this.messaging.publicLivechatGlobal.publicLivechat.operator.id;
                            const oneWeek = 7 * 24 * 60 * 60;
                            set_cookie('im_livechat_previous_operator_pid', operatorPidId, oneWeek);
                        }
                    });
                }
            }).then(() => {
                this.update({ isOpeningChat: false });
            }).guardedCatch(() => {
                this.update({ isOpeningChat: false });
            });
        },
        /**
         * Resuming the chatbot script if we are currently running one.
         *
         * In addition, we register a resize event on the window object to scroll messages to bottom.
         * This is done especially for mobile (Android) where the keyboard opens upon focusing the input
         * field and shrinks the whole window size.
         * Scrolling to the bottom allows the user to see the last messages properly when that happens.
         *
         * @private
         * @override
         */
        _openChatWindowChatbot() {
            window.addEventListener('resize', () => {
                if (this.chatWindow) {
                    this.chatWindow.publicLivechatView.widget.scrollToBottom();
                }
            });

            if (
                this.chatbot &&
                this.chatbot.currentStep &&
                this.chatbot.currentStep.data &&
                this.messaging.publicLivechatGlobal.messages &&
                this.messaging.publicLivechatGlobal.messages.length !== 0
            ) {
                this.widget._chatbotProcessStep();
            }
        },
        /**
         * @private
         * @param {Object} message
         */
        async _sendMessage(message) {
            this.messaging.publicLivechatGlobal.publicLivechat.legacyPublicLivechat._notifyMyselfTyping({ typing: false });
            const messageId = await this.messaging.rpc({
                route: '/mail/chat_post',
                params: { uuid: this.messaging.publicLivechatGlobal.publicLivechat.uuid, message_content: message.content },
            });
            if (!messageId) {
                try {
                    this.widget.displayNotification({
                        message: this.env._t("Session expired... Please refresh and try again."),
                        sticky: true,
                    });
                } catch (_err) {
                    /**
                     * Failure in displaying notification happens when
                     * notification service doesn't exist, which is the case
                     * in external lib. We don't want notifications in
                     * external lib at the moment because they use bootstrap
                     * toast and we don't want to include boostrap in
                     * external lib.
                     */
                    console.warn(this.env._t("Session expired... Please refresh and try again."));
                }
                this.closeChat();
            }
            this.chatWindow.publicLivechatView.widget.scrollToBottom();
        },
        /**
         * @private
         */
        _sendMessageChatbotAfter() {
            if (this.isChatbotRedirecting) {
                return;
            }
            if (
                this.isChatbot &&
                this.chatbot.currentStep &&
                this.chatbot.currentStep.data
            ) {
                if (
                    this.chatbot.currentStep.data.chatbot_step_type === 'forward_operator' &&
                    this.chatbot.currentStep.data.chatbot_operator_found
                ) {
                    return; // operator has taken over the conversation, let them speak
                } else if (this.chatbot.currentStep.data.chatbot_step_type === 'free_input_multi') {
                    this.widget._debouncedChatbotAwaitUserInput();
                } else if (!this.chatbot.shouldEndScript) {
                    this.chatbotSetIsTyping();
                    this.update({
                        chatbotNextStepTimeout: setTimeout(
                            this.widget._chatbotTriggerNextStep.bind(this.widget),
                            this.chatbot.messageDelay,
                        ),
                    });
                } else {
                    this.chatbotEndScript();
                }
                this.chatbotSaveSession();
            }
        },
        /**
         * When the Customer sends a message, we need to act depending on our current state:
         * - If the conversation has been forwarded to an operator
         *   Then there is nothing to do, we let them speak
         * - If we are currently on a 'free_input_multi' step
         *   Await more user input (see #_chatbotAwaitUserInput() for details)
         * - Otherwise we continue the script or end it if it's the last step
         *
         * We also save the current session state.
         * Important as this may be the very first interaction with the bot, we need to save right away
         * to correctly handle any page redirection / page refresh.
         *
         * Special side case: if we are currently redirecting to another page (see '_onChatbotOptionClicked')
         * we shortcut the process as we are currently moving to a different URL.
         * The script will be resumed on the new page (if in the same website domain).
         *
         * @private
         */
        async _sendMessageChatbotBefore() {
            if (
                this.isChatbot &&
                this.chatbot.currentStep &&
                this.chatbot.currentStep.data
            ) {
                await this.widget._chatbotPostWelcomeMessages();
            }
        },
        async _willStart() {
            const cookie = get_cookie('im_livechat_session');
            if (cookie) {
                const channel = JSON.parse(cookie);
                const history = await this.messaging.rpc({
                    route: '/mail/chat_history',
                    params: { uuid: channel.uuid, limit: 100 },
                });
                history.reverse();
                this.update({ history });
                for (const message of this.history) {
                    message.body = Markup(message.body);
                }
            } else {
                const result = await this.messaging.rpc({
                    route: '/im_livechat/init',
                    params: { channel_id: this.channelId },
                });
                if (!result.available_for_me) {
                    return Promise.reject();
                }
                this.update({ rule: result.rule });
            }
            return this.messaging.publicLivechatGlobal.loadQWebTemplate();
        },
        /**
         * This override handles the following use cases:
         *
         * - If the chat is started for the first time (first visit of a visitor)
         *   We register the chatbot configuration and the rest of the behavior is triggered by various
         *   method overrides ('sendWelcomeMessage', 'sendMessage', ...)
         *
         * - If the chat has been started before, but the user did not interact with the bot
         *   The default behavior is to open an empty chat window, without any messages.
         *   In addition, we fetch the configuration (with a '/init' call), to see if we have a bot
         *   configured.
         *   Indeed we want to trigger the bot script on every page where the associated rule is matched.
         *
         * - If we have a non-empty chat history, resume the chat script where the end-user left it by
         *   fetching the necessary information from the local storage.
         *
         * @override
         */
        async _willStartChatbot() {
            if (this.rule && !!this.chatbot) {
                // noop
            } else if (this.history !== null && this.history.length === 0) {
                this.update({
                    livechatInit: await this.messaging.rpc({
                        route: '/im_livechat/init',
                        params: { channel_id: this.channelId },
                    }),
                });
            } else if (this.history !== null && this.history.length !== 0) {
                const sessionCookie = get_cookie('im_livechat_session');
                if (sessionCookie) {
                    this.update({ sessionCookie });
                    if (localStorage.getItem(this.chatbotSessionCookieKey)) {
                        this.update({ chatbotState: 'restore_session' });
                    }
                }
            }

            if (this.chatbotState === 'init') {
                // we landed on a website page where a channel rule is configured to run a chatbot.script
                // -> initialize necessary state
                if (this.rule.chatbot_welcome_steps && this.rule.chatbot_welcome_steps.length !== 0) {
                    this.chatbot.update({
                        currentStep: insertAndReplace({
                            data: this.chatbot.lastWelcomeStep,
                        }),
                    });
                }
            } else if (this.chatbotState === 'welcome') {
                // we landed on a website page and a chatbot script was initialized on a previous one
                // however the end-user did not interact with the bot ( :( )
                // -> remove cookie to force opening the popup again
                // -> initialize necessary state
                // -> batch welcome message (see '_sendWelcomeChatbotMessage')
                set_cookie('im_livechat_auto_popup', '', -1);
                this.update({ history: clear() });
                this.update({ rule: this.livechatInit.rule });
            } else if (this.chatbotState === 'restore_session') {
                // we landed on a website page and a chatbot script is currently running
                // -> restore the user's session (see 'chatbotRestoreSession')
                this.chatbotRestoreSession();
            }
        },
    },
    fields: {
        autoOpenChatTimeout: attr(),
        buttonBackgroundColor: attr({
            compute: '_computeButtonBackgroundColor',
        }),
        buttonText: attr({
            compute: '_computeButtonText',
        }),
        buttonTextColor: attr({
            compute: '_computeButtonTextColor',
        }),
        channelId: attr({
            compute: '_computeChannelId',
        }),
        chatbot: one('Chatbot', {
            compute: '_computeChatbot',
            inverse: 'livechatButtonViewOwner',
            isCausal: true,
        }),
        chatbotNextStepTimeout: attr(),
        chatbotSessionCookieKey: attr({
            compute: '_computeChatbotSessionCookieKey',
        }),
        chatbotState: attr({
            compute: '_computeChatbotState',
        }),
        chatbotWelcomeMessageTimeout: attr(),
        chatWindow: one('PublicLivechatWindow', {
            inverse: 'livechatButtonViewOwner',
            isCausal: true,
        }),
        currentPartnerId: attr({
            compute: '_computeCurrentPartnerId',
        }),
        defaultMessage: attr({
            compute: '_computeDefaultMessage',
        }),
        defaultUsername: attr({
            compute: '_computeDefaultUsername',
        }),
        headerBackgroundColor: attr({
            compute: '_computeHeaderBackgroundColor',
        }),
        history: attr({
            default: null,
        }),
        inputPlaceholder: attr({
            compute: '_computeInputPlaceholder',
            default: '',
        }),
        isChatbot: attr({
            compute: '_computeIsChatbot',
            default: false,
        }),
        isChatbotRedirecting: attr({
            default: false,
        }),
        isOpenChatDebounced: attr({
            compute: '_computeIsOpenChatDebounced',
            default: true,
        }),
        isOpeningChat: attr({
            default: false,
        }),
        isTestChatbot: attr({
            default: false,
        }),
        isTypingTimeout: attr(),
        isWebsiteLivechatChatbotFlow: attr({
            default: false,
        }),
        livechatInit: attr(),
        localStorageChatbotState: attr({
            compute: '_computeLocalStorageChatbotState',
        }),
        openChatDebounced: attr({
            compute: '_computeOpenChatDebounced',
        }),
        publicLivechatGlobalOwner: one('PublicLivechatGlobal', {
            inverse: 'livechatButtonView',
            readonly: true,
            required: true,
        }),
        rule: attr(),
        serverUrl: attr({
            compute: '_computeServerUrl',
        }),
        sessionCookie: attr(),
        testChatbotData: attr(),
        titleColor: attr({
            compute: '_computeTitleColor',
        }),
        widget: attr(),
    },
});
