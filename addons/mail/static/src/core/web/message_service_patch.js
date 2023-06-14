/* @odoo-module */

import { sprintf } from "@web/core/utils/strings";
import { MessageService, setMessageDone } from "../common/message_service";
import { removeFollower } from "./thread_service_patch";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

let notificationService;

export async function unfollowMessage(message) {
    if (message.isNeedaction) {
        await setMessageDone(message);
    }
    const thread = message.originThread;
    await removeFollower(thread.followerOfSelf);
    notificationService.add(
        sprintf(_t('You are no longer following "%(thread_name)s".'), {
            thread_name: thread.name,
        }),
        { type: "success" }
    );
}

patch(MessageService.prototype, "mail/core/web", {
    setup(env, services) {
        this._super(env, services);
        notificationService = services.notification;
    },
});
