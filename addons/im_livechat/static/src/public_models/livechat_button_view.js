/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import {unaccent} from 'web.utils';
import {getCookie, setCookie, deleteCookie} from 'web.utils.cookies';

registerModel({
    name: 'LivechatButtonView',
    lifecycleHooks: {
        _created() {
            this.update({ widget: this.env.services.public_livechat_service.mountLivechatButton() });
        },
        _willDelete() {
            this.widget.destroy();
        },
    },
    recordMethods: {
        /**
         * @param {Object} data
         * @param {Object} [options={}]
         */
        addMessage(data, options) {
            const hasAlreadyMessage = _.some(this.messaging.publicLivechatGlobal.messages, function (msg) {
                return data.id === msg.id;
            });
            if (hasAlreadyMessage) {
                return;
            }
            const message = this.messaging.models['PublicLivechatMessage'].insert({
                data,
                id: data.id,
            });

            if (this.messaging.publicLivechatGlobal.publicLivechat && this.messaging.publicLivechatGlobal.publicLivechat.widget) {
                this.messaging.publicLivechatGlobal.publicLivechat.widget.addMessage(message.widget);
            }

            if (options && options.prepend) {
                this.messaging.publicLivechatGlobal.update({
                    messages: [message, ...this.messaging.publicLivechatGlobal.messages],
                });
            } else {
                this.messaging.publicLivechatGlobal.update({
                    messages: [...this.messaging.publicLivechatGlobal.messages, message],
                });
            }
        },
        askFeedback() {
            this.messaging.publicLivechatGlobal.chatWindow.widget.$('.o_thread_composer input').prop('disabled', true);
            this.messaging.publicLivechatGlobal.update({ feedbackView: {} });
            /**
             * When we enter the "ask feedback" process of the chat, we hide some elements that become
             * unnecessary and irrelevant (restart / end messages, any text field values, ...).
             */
            if (
                this.messaging.publicLivechatGlobal.chatbot.currentStep &&
                this.messaging.publicLivechatGlobal.chatbot.currentStep.data
            ) {
                this.messaging.publicLivechatGlobal.chatbot.currentStep.data.conversation_closed = true;
                this.messaging.publicLivechatGlobal.chatbot.saveSession();
            }
            this.messaging.publicLivechatGlobal.chatWindow.widget.$('.o_livechat_chatbot_main_restart').addClass('d-none');
            this.messaging.publicLivechatGlobal.chatWindow.widget.$('.o_livechat_chatbot_end').hide();
            this.messaging.publicLivechatGlobal.chatWindow.widget.$('.o_composer_text_field')
                .removeClass('d-none')
                .val('');
        },
        /**
         * Restart the script and then trigger the "next step" (which will be the first of the script
         * in this case).
         */
        async onChatbotRestartScript(ev) {
            this.messaging.publicLivechatGlobal.chatWindow.widget.$('.o_composer_text_field').removeClass('d-none');
            this.messaging.publicLivechatGlobal.chatWindow.widget.$('.o_livechat_chatbot_end').hide();

            if (this.messaging.publicLivechatGlobal.chatbot.nextStepTimeout) {
                clearTimeout(this.messaging.publicLivechatGlobal.chatbot.nextStepTimeout);
            }

            if (this.messaging.publicLivechatGlobal.chatbot.welcomeMessageTimeout) {
                clearTimeout(this.messaging.publicLivechatGlobal.chatbot.welcomeMessageTimeout);
            }

            const postedMessage = await this.messaging.rpc({
                route: '/chatbot/restart',
                params: {
                    channel_uuid: this.messaging.publicLivechatGlobal.publicLivechat.uuid,
                    chatbot_script_id: this.messaging.publicLivechatGlobal.chatbot.scriptId,
                },
            });

            if (postedMessage) {
                this.messaging.publicLivechatGlobal.chatbot.addMessage(postedMessage);
            }

            this.messaging.publicLivechatGlobal.chatbot.update({ currentStep: clear() });
            this.messaging.publicLivechatGlobal.chatbot.setIsTyping();
            this.messaging.publicLivechatGlobal.chatbot.update({
                nextStepTimeout: setTimeout(
                    this.messaging.publicLivechatGlobal.chatbot.triggerNextStep,
                    this.messaging.publicLivechatGlobal.chatbot.messageDelay,
                ),
            });
        },
        closeChat() {
            this.messaging.publicLivechatGlobal.update({ chatWindow: clear() });
            deleteCookie('im_livechat_session');
        },
        /**
         * Called when the visitor leaves the livechat chatter the first time (first click on X button)
         * this will deactivate the mail_channel, notify operator that visitor has left the channel.
         */
        leaveSession() {
            const cookie = getCookie('im_livechat_session');
            if (cookie) {
                const channel = JSON.parse(cookie);
                this.messaging.rpc({ route: '/im_livechat/visitor_leave_session', params: { uuid: channel.uuid } });
                deleteCookie('im_livechat_session');
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
            this.messaging.publicLivechatGlobal.update({ chatWindow: {} });
            await this.messaging.publicLivechatGlobal.chatWindow.widget.appendTo($('body'));
            const cssProps = { bottom: 0 };
            cssProps[this.messaging.locale.textDirection === 'rtl' ? 'left' : 'right'] = 0;
            this.messaging.publicLivechatGlobal.chatWindow.widget.$el.css(cssProps);
            this.widget.$el.hide();
            this._openChatWindowChatbot();
        },
        /**
         * @param {Object} message
         */
        async sendMessage(message) {
            await this._sendMessageChatbotBefore();
            await this._sendMessage(message);
            this._sendMessageChatbotAfter();
        },
        start() {
            if (!this.messaging.publicLivechatGlobal.hasWebsiteLivechatFeature) {
                this.widget.$el.text(this.buttonText);
            }
            this.update({ isWidgetMounted: true });
            if (this.messaging.publicLivechatGlobal.history) {
                for (const m of this.messaging.publicLivechatGlobal.history) {
                    this.addMessage(m);
                }
                this.openChat();
            } else if (!this.messaging.device.isSmall && this.messaging.publicLivechatGlobal.rule.action === 'auto_popup') {
                const autoPopupCookie = getCookie('im_livechat_auto_popup');
                if (!autoPopupCookie || JSON.parse(autoPopupCookie)) {
                    this.update({
                        autoOpenChatTimeout: setTimeout(
                            this.openChat,
                            this.messaging.publicLivechatGlobal.rule.auto_popup_timer * 1000,
                        ),
                    });
                }
            }
            if (this.buttonBackgroundColor) {
                this.widget.$el.css('background-color', this.buttonBackgroundColor);
            }
            if (this.buttonTextColor) {
                this.widget.$el.css('color', this.buttonTextColor);
            }
            // If website_event_track installed, put the livechat banner above the PWA banner.
            const pwaBannerHeight = $('.o_pwa_install_banner').outerHeight(true);
            if (pwaBannerHeight) {
                this.widget.$el.css('bottom', pwaBannerHeight + 'px');
            }
        },
        /**
         * @private
         */
        _openChat() {
            if (this.isOpeningChat) {
                return;
            }
            const cookie = getCookie('im_livechat_session');
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
                        publicLivechat: { data: livechatData },
                    });
                    return this.openChatWindow().then(() => {
                        if (!this.messaging.publicLivechatGlobal.history) {
                            this.widget._sendWelcomeMessage();
                        }
                        this.messaging.publicLivechatGlobal.chatWindow.renderMessages();
                        this.messaging.publicLivechatGlobal.update({ notificationHandler: {} });

                        setCookie('im_livechat_session', unaccent(JSON.stringify(this.messaging.publicLivechatGlobal.publicLivechat.widget.toData()), true), 60 * 60, 'required');
                        setCookie('im_livechat_auto_popup', JSON.stringify(false), 60 * 60, 'optional');
                        if (this.messaging.publicLivechatGlobal.publicLivechat.operator) {
                            const operatorPidId = this.messaging.publicLivechatGlobal.publicLivechat.operator.id;
                            const oneWeek = 7 * 24 * 60 * 60;
                            setCookie('im_livechat_previous_operator_pid', operatorPidId, oneWeek, 'optional');
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
                if (this.messaging.publicLivechatGlobal.chatWindow) {
                    this.messaging.publicLivechatGlobal.chatWindow.publicLivechatView.widget.scrollToBottom();
                }
            });

            if (
                this.messaging.publicLivechatGlobal.chatbot.currentStep &&
                this.messaging.publicLivechatGlobal.chatbot.currentStep.data &&
                this.messaging.publicLivechatGlobal.messages &&
                this.messaging.publicLivechatGlobal.messages.length !== 0
            ) {
                this.messaging.publicLivechatGlobal.chatbot.processStep();
            }
        },
        /**
         * @private
         * @param {Object} message
         */
        async _sendMessage(message) {
            this.messaging.publicLivechatGlobal.publicLivechat.widget._notifyMyselfTyping({ typing: false });
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
            this.messaging.publicLivechatGlobal.chatWindow.publicLivechatView.widget.scrollToBottom();
        },
        /**
         * @private
         */
        _sendMessageChatbotAfter() {
            if (this.messaging.publicLivechatGlobal.chatbot.isRedirecting) {
                return;
            }
            if (
                this.messaging.publicLivechatGlobal.chatbot.isActive &&
                this.messaging.publicLivechatGlobal.chatbot.currentStep &&
                this.messaging.publicLivechatGlobal.chatbot.currentStep.data
            ) {
                if (
                    this.messaging.publicLivechatGlobal.chatbot.currentStep.data.chatbot_step_type === 'forward_operator' &&
                    this.messaging.publicLivechatGlobal.chatbot.currentStep.data.chatbot_operator_found
                ) {
                    return; // operator has taken over the conversation, let them speak
                } else if (this.messaging.publicLivechatGlobal.chatbot.currentStep.data.chatbot_step_type === 'free_input_multi') {
                    this.messaging.publicLivechatGlobal.chatbot.debouncedAwaitUserInput();
                } else if (!this.messaging.publicLivechatGlobal.chatbot.shouldEndScript) {
                    this.messaging.publicLivechatGlobal.chatbot.setIsTyping();
                    this.messaging.publicLivechatGlobal.chatbot.update({
                        nextStepTimeout: setTimeout(
                            this.messaging.publicLivechatGlobal.chatbot.triggerNextStep,
                            this.messaging.publicLivechatGlobal.chatbot.messageDelay,
                        ),
                    });
                } else {
                    this.messaging.publicLivechatGlobal.chatbot.endScript();
                }
                this.messaging.publicLivechatGlobal.chatbot.saveSession();
            }
        },
        /**
         * When the Customer sends a message, we need to act depending on our current state:
         * - If the conversation has been forwarded to an operator
         *   Then there is nothing to do, we let them speak
         * - If we are currently on a 'free_input_multi' step
         *   Await more user input (see #Chatbot/awaitUserInput for details)
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
                this.messaging.publicLivechatGlobal.chatbot.isActive &&
                this.messaging.publicLivechatGlobal.chatbot.currentStep &&
                this.messaging.publicLivechatGlobal.chatbot.currentStep.data
            ) {
                await this.messaging.publicLivechatGlobal.chatbot.postWelcomeMessages();
            }
        },
    },
    fields: {
        autoOpenChatTimeout: attr(),
        buttonBackgroundColor: attr({
            compute() {
                return this.messaging.publicLivechatGlobal.options.button_background_color;
            },
        }),
        buttonText: attr({
            compute() {
                if (this.messaging.publicLivechatGlobal.options.button_text) {
                    return this.messaging.publicLivechatGlobal.options.button_text;
                }
                return this.env._t("Chat with one of our collaborators");
            },
        }),
        buttonTextColor: attr({
            compute() {
                return this.messaging.publicLivechatGlobal.options.button_text_color;
            },
        }),
        chatbotNextStepTimeout: attr(),
        chatbotWelcomeMessageTimeout: attr(),
        currentPartnerId: attr({
            compute() {
                if (!this.messaging.publicLivechatGlobal.isAvailable) {
                    return clear();
                }
                return this.messaging.publicLivechatGlobal.options.current_partner_id;
            },
        }),
        defaultMessage: attr({
            compute() {
                if (this.messaging.publicLivechatGlobal.options.default_message) {
                    return this.messaging.publicLivechatGlobal.options.default_message;
                }
                return this.env._t("How may I help you?");
            },
        }),
        defaultUsername: attr({
            compute() {
                if (this.messaging.publicLivechatGlobal.options.default_username) {
                    return this.messaging.publicLivechatGlobal.options.default_username;
                }
                return this.env._t("Visitor");
            },
        }),
        headerBackgroundColor: attr({
            compute() {
                return this.messaging.publicLivechatGlobal.options.header_background_color;
            },
        }),
        inputPlaceholder: attr({
            compute() {
                if (this.messaging.publicLivechatGlobal.chatbot.isActive) {
                    // void the default livechat placeholder in the user input
                    // as we use it for specific things (e.g: showing "please select an option above")
                    return clear();
                }
                if (this.messaging.publicLivechatGlobal.options.input_placeholder) {
                    return this.messaging.publicLivechatGlobal.options.input_placeholder;
                }
                return this.env._t("Ask something ...");
            },
            default: '',
        }),
        isOpenChatDebounced: attr({
            compute() {
                return clear();
            },
            default: true,
        }),
        isOpeningChat: attr({
            default: false,
        }),
        isTypingTimeout: attr(),
        isWidgetMounted: attr({
            default: false,
        }),
        openChatDebounced: attr({
            compute() {
                return _.debounce(this._openChat, 200, true);
            },
        }),
        publicLivechatGlobalOwner: one('PublicLivechatGlobal', {
            identifying: true,
            inverse: 'livechatButtonView',
        }),
        serverUrl: attr({
            compute() {
                return this.messaging.publicLivechatGlobal.serverUrl;
            },
        }),
        titleColor: attr({
            compute() {
                return this.messaging.publicLivechatGlobal.options.title_color;
            },
        }),
        widget: attr(),
    },
});
