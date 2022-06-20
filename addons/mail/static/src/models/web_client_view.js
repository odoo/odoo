/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insert, insertAndReplace, link, replace } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';

export const getNextId = (function () {
    let tmpId = 0;
    return () => {
        tmpId += 1;
        return tmpId;
    };
})();

const getThreadNextTemporaryId = (function () {
    let tmpId = 0;
    return () => {
        tmpId -= 1;
        return tmpId;
    };
})();

const getMessageNextTemporaryId = (function () {
    let tmpId = 0;
    return () => {
        tmpId -= 1;
        return tmpId;
    };
})();

registerModel({
    name: 'WebClientView',
    identifyingFields: ['id'],
    recordMethods: {
        /**
         * @private
         */
        _onThreadIdOrThreadModelChanged() {
            if (this.threadId) {
                if (this.thread && this.thread.isTemporary) {
                    this.thread.delete();
                }
                this.update({
                    thread: insert({
                        // If the thread was considered to have the activity
                        // mixin once, it will have it forever.
                        hasActivities: this.chatter && this.chatter.hasActivities ? true : undefined,
                        id: this.threadId,
                        model: this.threadModel,
                    }),
                });
                if (this.chatter) {
                    this.chatter.update({
                        attachmentBoxView: this.chatter.isAttachmentBoxVisibleInitially ? insertAndReplace() : clear(),
                    });
                }
            } else if (!this.thread || !this.thread.isTemporary) {
                const currentPartner = this.messaging.currentPartner;
                const message = this.messaging.models['Message'].create({
                    author: replace(currentPartner),
                    body: this.env._t("Creating a new record..."),
                    id: getMessageNextTemporaryId(),
                    isTemporary: true,
                });
                const nextId = getThreadNextTemporaryId();
                this.update({
                    thread: insert({
                        areAttachmentsLoaded: true,
                        id: nextId,
                        isTemporary: true,
                        model: this.threadModel,
                    }),
                });
                if (this.chatter) {
                    this.chatter.update({ attachmentBoxView: clear() });
                }
                this.thread.cache.update({ messages: link(message) });
            }
        },
    },
    fields: {
        chatter: one('Chatter', {
            inverse: 'webClientViewOwner',
            isCausal: true,
        }),
        /**
         * States the id of this web client view. This id does not correspond to
         * any specific value, it is just a unique identifier given by the creator
         * of this record.
         */
        id: attr({
            readonly: true,
            required: true,
        }),
        thread: one('Thread'),
        /**
         * Determines the id of the thread that will be displayed by `this`.
         */
        threadId: attr(),
        /**
         * Determines the model of the thread that will be displayed by `this`.
         */
        threadModel: attr({
            required: true,
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['threadId', 'threadModel'],
            methodName: '_onThreadIdOrThreadModelChanged',
        }),
    ],
});
