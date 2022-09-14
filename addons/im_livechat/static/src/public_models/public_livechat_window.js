/** @odoo-module **/

import PublicLivechatWindow from '@im_livechat/legacy/widgets/public_livechat_window/public_livechat_window';

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'PublicLivechatWindow',
    lifecycleHooks: {
        _created() {
            this.update({
                widget: new PublicLivechatWindow(
                    this.global.PublicLivechatGlobal.livechatButtonView.widget,
                    this.messaging,
                    this.global.PublicLivechatGlobal.publicLivechat.widget,
                ),
            });
        },
        _willDelete() {
            this.widget.destroy();
        },
    },
    recordMethods: {
        enableInput() {
            const $composerTextField = this.widget.$('.o_composer_text_field');
            $composerTextField
                .prop('disabled', false)
                .removeClass('text-center fst-italic bg-200')
                .val('')
                .focus();

            $composerTextField.off('keydown', this.global.PublicLivechatGlobal.chatbot.onKeydownInput);
            if (this.global.PublicLivechatGlobal.chatbot.currentStep.data.chatbot_step_type === 'free_input_multi') {
                $composerTextField.on('keydown', this.global.PublicLivechatGlobal.chatbot.onKeydownInput);
            }
        },
        /**
         * Disable the input allowing the user to type.
         * This is typically used when we want to force him to click on one of the chatbot options.
         *
         * @private
         */
        disableInput(disableText) {
            this.widget.$('.o_composer_text_field')
                .prop('disabled', true)
                .addClass('text-center fst-italic bg-200')
                .val(disableText);
        },
        renderMessages() {
            const shouldScroll = !this.isFolded && this.publicLivechatView.widget.isAtBottom();
            this.widget.render();
            if (shouldScroll) {
                this.publicLivechatView.widget.scrollToBottom();
            }
            const self = this;

            this.widget.$('.o_thread_message:last .o_livechat_chatbot_options li').each(function () {
                $(this).on('click', self.global.PublicLivechatGlobal.livechatButtonView.widget._onChatbotOptionClicked.bind(self.global.PublicLivechatGlobal.livechatButtonView.widget));
            });

            this.widget.$('.o_livechat_chatbot_main_restart').on('click', (ev) => {
                ev.stopPropagation(); // prevent fold behaviour
                this.global.PublicLivechatGlobal.livechatButtonView.onChatbotRestartScript(ev);
            });

            if (this.global.PublicLivechatGlobal.messages.length !== 0) {
                const lastMessage = this.global.PublicLivechatGlobal.lastMessage;
                const stepAnswers = lastMessage.widget.getChatbotStepAnswers();
                if (stepAnswers && stepAnswers.length !== 0 && !lastMessage.widget.getChatbotStepAnswerId()) {
                    this.disableInput(this.env._t("Select an option above"));
                }
            }
        },
    },
    fields: {
        inputPlaceholder: attr({
            compute() {
                if (this.global.PublicLivechatGlobal.livechatButtonView.inputPlaceholder) {
                    return this.global.PublicLivechatGlobal.livechatButtonView.inputPlaceholder;
                }
                return this.env._t("Say something");
            },
        }),
        publicLivechatGlobalOwner: one('PublicLivechatGlobal', {
            identifying: true,
            inverse: 'chatWindow',
        }),
        publicLivechatView: one('PublicLivechatView', {
            default: {},
            inverse: 'publicLivechatWindowOwner',
        }),
        widget: attr(),
    },
});
