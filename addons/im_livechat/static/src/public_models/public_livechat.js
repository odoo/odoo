/** @odoo-module **/

import PublicLivechat from '@im_livechat/legacy/models/public_livechat';

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import { unaccent } from 'web.utils';
import { deleteCookie, setCookie } from 'web.utils.cookies';

registerModel({
    name: 'PublicLivechat',
    lifecycleHooks: {
        _created() {
            this.update({
                widget: new PublicLivechat(this.messaging, {
                    parent: this.publicLivechatGlobalOwner.livechatButtonView.widget,
                    data: this.data,
                }),
            });
        },
        _willDelete() {
            this.widget.destroy();
        },
    },
    recordMethods: {
        async createLivechatChannel() {
            const livechatData = await this.messaging.rpc({
                route: "/im_livechat/get_session",
                params: this.messaging.publicLivechatGlobal.livechatButtonView.widget._prepareGetSessionParameters(),
            });
            if (!livechatData || !livechatData.operator_pid) {
                this.update({ data: clear() });
                deleteCookie("im_livechat_session");
                this.messaging.publicLivechatGlobal.chatWindow.widget.renderChatWindow();
            } else {
                this.update({ data: livechatData });
                this.widget.data = livechatData;
                this.updateSessionCookie();
            }
        },
        updateSessionCookie() {
            deleteCookie("im_livechat_session");
            setCookie(
                "im_livechat_session",
                unaccent(JSON.stringify(this.widget.toData()), true),
                60 * 60,
                "required"
            );
            setCookie("im_livechat_auto_popup", JSON.stringify(false), 60 * 60, "optional");
            if (this.operator) {
                const operatorPidId = this.operator.id;
                const oneWeek = 7 * 24 * 60 * 60;
                setCookie("im_livechat_previous_operator_pid", operatorPidId, oneWeek, "optional");
            }
        },
    },
    fields: {
        data: attr(),
        id: attr({
            compute() {
                if (!this.data) {
                    return clear();
                }
                return this.data.id;
            },
        }),
        isFolded: attr({
            default: false,
        }),
        isTemporary: attr({
            compute() {
                if (!this.data || !this.data.id) {
                    return true;
                }
                return false;
            },
        }),
        publicLivechatGlobalOwner: one('PublicLivechatGlobal', {
            identifying: true,
            inverse: 'publicLivechat',
        }),
        name: attr({
            compute() {
                if (!this.data || !this.operator) {
                    return clear();
                }
                return this.data.name;
            },
        }),
        operator: one('LivechatOperator', {
            compute() {
                if (!this.data) {
                    return clear();
                }
                if (!this.data.operator_pid) {
                    return clear();
                }
                if (!this.data.operator_pid[0]) {
                    return clear();
                }
                return {
                    id: this.data.operator_pid[0],
                    name: this.data.operator_pid[1],
                };
            },
        }),
        status: attr({
            compute() {
                if (!this.data) {
                    return clear();
                }
                return this.data.status || '';
            },
        }),
        // amount of messages that have not yet been read on this chat
        unreadCounter: attr({
            default: 0,
        }),
        uuid: attr({
            compute() {
                if (!this.data) {
                    return clear();
                }
                return this.data.uuid;
            },
        }),
        widget: attr(),
    },
});
