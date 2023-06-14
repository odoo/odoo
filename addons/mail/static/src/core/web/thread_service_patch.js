/* @odoo-module */

import { Follower } from "@mail/core/common/follower_model";
import {
    ThreadService,
    fetchNewMessages,
    insertThread,
    openThread,
    setMainAttachmentFromIndex,
    threadService,
    updateThread,
} from "@mail/core/common/thread_service";
import { parseEmail } from "@mail/js/utils";
import { createLocalId } from "@mail/utils/common/misc";
import { patchFn } from "@mail/utils/common/patch";

import { markup } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { getNextMessageTemporaryId, insertMessage } from "../common/message_service";
import { insertAttachment } from "../common/attachment_service";
import { openChatWindow } from "../common/chat_window_service";
import { insertPersona } from "../common/persona_service";
import { deleteActivity, insertActivity } from "./activity_service";

let nextId = 1;

let gEnv;
let orm;
let rpc;
let store;
let ui;

/**
 * @param {import("@mail/core/common/thread_model").Thread} thread
 * @param {['activities'|'followers'|'attachments'|'messages'|'suggestedRecipients']} requestList
 */
export async function fetchThreadData(
    thread,
    requestList = ["activities", "followers", "attachments", "messages", "suggestedRecipients"]
) {
    thread.isLoadingAttachments =
        thread.isLoadingAttachments || requestList.includes("attachments");
    if (requestList.includes("messages")) {
        fetchNewMessages(thread);
    }
    const result = await rpc("/mail/thread/data", {
        request_list: requestList,
        thread_id: thread.id,
        thread_model: thread.model,
    });
    if ("attachments" in result) {
        result["attachments"] = result["attachments"].map((attachment) => ({
            ...attachment,
            originThread: insertThread(attachment.originThread[0][1]),
        }));
    }
    thread.canPostOnReadonly = result.canPostOnReadonly;
    thread.hasReadAccess = result.hasReadAccess;
    thread.hasWriteAccess = result.hasWriteAccess;
    if ("activities" in result) {
        const existingIds = new Set();
        for (const activity of result.activities) {
            if (activity.note) {
                activity.note = markup(activity.note);
            }
            existingIds.add(insertActivity(activity).id);
        }
        for (const activity of thread.activities) {
            if (!existingIds.has(activity.id)) {
                deleteActivity(activity);
            }
        }
    }
    if ("attachments" in result) {
        updateThread(thread, {
            areAttachmentsLoaded: true,
            attachments: result.attachments,
            isLoadingAttachments: false,
        });
    }
    if ("mainAttachment" in result) {
        thread.mainAttachment = result.mainAttachment.id
            ? insertAttachment(result.mainAttachment)
            : undefined;
    }
    if (!thread.mainAttachment && thread.attachmentsInWebClientView.length > 0) {
        setMainAttachmentFromIndex(thread, 0);
    }
    if ("followers" in result) {
        for (const followerData of result.followers) {
            insertFollower({
                followedThread: thread,
                ...followerData,
            });
        }
    }
    if ("suggestedRecipients" in result) {
        insertSuggestedRecipients(thread, result.suggestedRecipients);
    }
    return result;
}

export function getThread(resModel, resId) {
    const localId = createLocalId(resModel, resId);
    if (localId in store.threads) {
        if (resId === false) {
            return store.threads[localId];
        }
        // to force a reload
        store.threads[localId].status = "new";
    }
    const thread = insertThread({
        id: resId,
        model: resModel,
        type: "chatter",
    });
    if (resId === false) {
        const tmpId = getNextMessageTemporaryId();
        const tmpData = {
            id: tmpId,
            author: { id: store.self.id },
            body: _t("Creating a new record..."),
            message_type: "notification",
            trackingValues: [],
            res_id: thread.id,
            model: thread.model,
        };
        const message = insertMessage(tmpData);
        thread.messages.push(message);
    }
    return thread;
}

/**
 * @param {import("@mail/core/common/follower_model").Data} data
 * @returns {import("@mail/core/common/follower_model").Follower}
 */
export function insertFollower(data) {
    let follower = store.followers[data.id];
    if (!follower) {
        store.followers[data.id] = new Follower();
        follower = store.followers[data.id];
    }
    Object.assign(follower, {
        followedThread: data.followedThread,
        id: data.id,
        isActive: data.is_active,
        partner: insertPersona({ ...data.partner, type: "partner" }),
        _store: store,
    });
    if (!follower.followedThread.followers.includes(follower)) {
        follower.followedThread.followers.push(follower);
    }
    return follower;
}

/**
 * @param {import("@mail/core/common/thread_model").Thread} thread
 * @param {import("@mail/core/web/suggested_recipient").SuggestedRecipient[]} dataList
 */
async function insertSuggestedRecipients(thread, dataList) {
    const recipients = [];
    for (const data of dataList) {
        const [partner_id, emailInfo, lang, reason] = data;
        const [name, email] = emailInfo && parseEmail(emailInfo);
        recipients.push({
            id: nextId++,
            name,
            email,
            lang,
            reason,
            persona: partner_id
                ? insertPersona({
                      type: "partner",
                      id: partner_id,
                  })
                : false,
            checked: partner_id ? true : false,
        });
    }
    thread.suggestedRecipients = recipients;
}

patchFn(openThread, function (thread, replaceNewMessageChatWindow) {
    if (!store.discuss.isActive || ui.isSmall) {
        openChatWindow(thread, replaceNewMessageChatWindow);
        return;
    }
    this._super(thread, replaceNewMessageChatWindow);
});

/**
 * @param {import("@mail/core/common/follower_model").Follower} follower
 */
export async function removeFollower(follower) {
    await orm.call(follower.followedThread.model, "message_unsubscribe", [
        [follower.followedThread.id],
        [follower.partner.id],
    ]);
    const index = follower.followedThread.followers.indexOf(follower);
    if (index !== -1) {
        follower.followedThread.followers.splice(index, 1);
    }
    delete store.followers[follower.id];
}

patch(ThreadService.prototype, "mail/core/web", {
    setup(env, services) {
        this._super(env, services);
        gEnv = env;
        orm = services.orm;
        rpc = services.rpc;
        store = services["mail.store"];
        ui = services.ui;
        // this prevents cyclic dependencies between insertFollower and other services
        gEnv.bus.addEventListener("core/web/thread_service.insertFollower", ({ detail }) => {
            insertFollower(detail);
        });
        // this prevents cyclic dependencies between getThread and other services
        gEnv.bus.addEventListener("core/web/thread_service.getThread", ({ detail }) => {
            detail.cb(getThread(...detail.params));
        });
    },
});

patch(threadService, "mail/core/web", {
    dependencies: [
        ...threadService.dependencies,
        "mail.activity",
        "mail.attachment",
        "mail.chat_window",
    ],
});
