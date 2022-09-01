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
                    this.messaging.publicLivechatGlobal.livechatButtonView.widget,
                    this.messaging,
                    this.messaging.publicLivechatGlobal.publicLivechat.widget,
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

            $composerTextField.off('keydown', this.messaging.publicLivechatGlobal.chatbot.onKeydownInput);
            if (this.messaging.publicLivechatGlobal.chatbot.currentStep.data.chatbot_step_type === 'free_input_multi') {
                $composerTextField.on('keydown', this.messaging.publicLivechatGlobal.chatbot.onKeydownInput);
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
                $(this).on('click', self.messaging.publicLivechatGlobal.livechatButtonView.widget._onChatbotOptionClicked.bind(self.messaging.publicLivechatGlobal.livechatButtonView.widget));
            });

            this.widget.$('.o_livechat_chatbot_main_restart').on('click',
                this.messaging.publicLivechatGlobal.livechatButtonView.onChatbotRestartScript
            );

            if (this.messaging.publicLivechatGlobal.messages.length !== 0) {
                const lastMessage = this.messaging.publicLivechatGlobal.lastMessage;
                const stepAnswers = lastMessage.widget.getChatbotStepAnswers();
                if (stepAnswers && stepAnswers.length !== 0 && !lastMessage.widget.getChatbotStepAnswerId()) {
                    this.disableInput(this.env._t("Select an option above"));
                }
            }
        },
        /**
         * @private
         * @returns {string}
         */
        _computeInputPlaceholder() {
            if (this.messaging.publicLivechatGlobal.livechatButtonView.inputPlaceholder) {
                return this.messaging.publicLivechatGlobal.livechatButtonView.inputPlaceholder;
            }
            return this.env._t("Say something");
        },
    },
    fields: {
        inputPlaceholder: attr({
            compute: '_computeInputPlaceholder',
        }),
        publicLivechatGlobalOwner: one('PublicLivechatGlobal', {
            identifying: true,
            inverse: 'chatWindow',
        }),
        publicLivechatView: one('PublicLivechatView', {
            default: {},
            inverse: 'publicLivechatWindowOwner',
            isCausal: true,
        }),
        widget: attr(),
    },
});
