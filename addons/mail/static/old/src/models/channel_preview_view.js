/** @odoo-module **/

import { useRefToModel } from "@mail/component_hooks/use_ref_to_model";
import { registerModel } from "@mail/model/model_core";
import { attr, one } from "@mail/model/model_field";
import { clear } from "@mail/model/model_field_command";
import { htmlToTextContentInline } from "@mail/js/utils";

registerModel({
    name: "ChannelPreviewView",
    template: "mail.ChannelPreviewView",
    templateGetter: "channelPreviewView",
    componentSetup() {
        useRefToModel({ fieldName: "markAsReadRef", refName: "markAsRead" });
    },
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            if (!this.exists()) {
                return;
            }
            const markAsRead = this.markAsReadRef.el;
            if (markAsRead && markAsRead.contains(ev.target)) {
                // handled in `_onClickMarkAsRead`
                return;
            }
            this.thread.open();
            if (!this.messaging.device.isSmall) {
                this.messaging.messagingMenu.close();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickMarkAsRead(ev) {
            if (this.thread.lastNonTransientMessage) {
                this.thread.markAsSeen(this.thread.lastNonTransientMessage);
            }
        },
    },
    fields: {
        channel: one("Channel", { identifying: true, inverse: "channelPreviewViews" }),
        imageUrl: attr({
            compute() {
                if (this.channel.correspondent) {
                    return this.channel.correspondent.avatarUrl;
                }
                return `/web/image/mail.channel/${this.channel.id}/avatar_128?unique=${this.channel.avatarCacheKey}`;
            },
        }),
        inlineLastMessageBody: attr({
            default: "",
            compute() {
                if (!this.thread || !this.thread.lastMessage) {
                    return clear();
                }
                return htmlToTextContentInline(this.thread.lastMessage.prettyBody);
            },
        }),
        isEmpty: attr({
            compute() {
                return !this.inlineLastMessageBody && !this.lastTrackingValue;
            },
        }),
        lastTrackingValue: one("TrackingValue", {
            compute() {
                if (
                    this.thread &&
                    this.thread.lastMessage &&
                    this.thread.lastMessage.lastTrackingValue
                ) {
                    return this.thread.lastMessage.lastTrackingValue;
                }
                return clear();
            },
        }),
        /**
         * Reference of the "mark as read" button. Useful to disable the
         * top-level click handler when clicking on this specific button.
         */
        markAsReadRef: attr(),
        messageAuthorPrefixView: one("MessageAuthorPrefixView", {
            inverse: "channelPreviewViewOwner",
            compute() {
                if (this.thread && this.thread.lastMessage && this.thread.lastMessage.author) {
                    return {};
                }
                return clear();
            },
        }),
        notificationListViewOwner: one("NotificationListView", {
            identifying: true,
            inverse: "channelPreviewViews",
        }),
        personaImStatusIconView: one("PersonaImStatusIconView", {
            inverse: "channelPreviewViewOwner",
            compute() {
                if (!this.channel.correspondent) {
                    return clear();
                }
                if (this.channel.correspondent.isImStatusSet) {
                    return {};
                }
                return clear();
            },
        }),
        thread: one("Thread", { related: "channel.thread" }),
    },
});
