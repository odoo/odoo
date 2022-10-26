/** @odoo-module **/

import { attr, clear, many, one, Model } from '@mail/model';

Model({
    name: 'Persona',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * Synchronize the current persona's identities (user/partner).
         */
         async sync() {
            if (this.guest) {
                return;
            }
            if (!this.partner.user && !this.partner.hasCheckedUser) {
                await this.partner.checkIsUser();
            }
        },
        /**
         * Gets the chat between this persona and the current partner.
         *
         * @returns {Channel|undefined}
         */
        async getChat() {
            // Find the chat or try to create it.
            let chat = this.partner.dmChatWithCurrentPartner;
            if (!chat || !chat.thread.isPinned) {
                // If chat is not pinned then it has to be pinned client-side
                // and server-side, which is a side effect of following rpc.
                chat = await this.messaging.models['Channel'].performRpcCreateChat({
                    partnerIds: [this.partner.id],
                });
            }
            return chat;
        },
        /**
         * Try to open a chat between this persona and the current partner.
         * If the chat can't be opened, display a notification instead.
         *
         * @param {Object} param0
         */
        async openChat({ inChatWindow, ...openThreadOptions } = {}) {
            if (!this.canOpenChat) {
                this.messaging.notify({
                    message: this.env._t('You can only chat with partners that have a dedicated user.'),
                    type: 'info',
                });
                return;
            }
            const chat = await this.getChat();
            if (!chat) {
                this.messaging.notify({
                    message: this.env._t("An unexpected error occurred during the creation of the chat."),
                    type: 'warning',
                });
                return;
            }
            if (inChatWindow) {
                return this.messaging.chatWindowManager.openThread(chat.thread, openThreadOptions);
            }
            return chat.thread.open(openThreadOptions);
        },
    },
    fields: {
        canOpenChat: attr({
            compute() {
                if (this.guest) {
                    return false;
                }
                return Boolean(this.partner.user);
            },
        }),
        channelMembers: many('ChannelMember', { inverse: 'persona', isCausal: true }),
        guest: one('Guest', { identifying: true, inverse: 'persona' }),
        im_status: attr({
            compute() {
                if (this.guest) {
                    return this.guest.im_status || clear();
                }
                if (this.partner) {
                    return this.partner.im_status || clear();
                }
                return clear();
            },
        }),
        messagingAsAnyPersona: one('Messaging', { default: {}, inverse: 'allPersonas' }),
        name: attr({
            compute() {
                if (this.guest) {
                    return this.guest.name || clear();
                }
                if (this.partner) {
                    return this.partner.nameOrDisplayName || clear();
                }
                return clear();
            },
        }),
        partner: one('Partner', { identifying: true, inverse: 'persona' }),
        volumeSetting: one('res.users.settings.volumes', {
            compute() {
                if (this.guest) {
                    return this.guest.volumeSetting || clear();
                }
                if (this.partner) {
                    return this.partner.volumeSetting || clear();
                }
                return clear();
            },
        }),
    },
});
