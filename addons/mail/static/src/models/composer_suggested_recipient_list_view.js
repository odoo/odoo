/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'ComposerSuggestedRecipientListView',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickShowLess(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ hasShowMoreButton: false });
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickShowMore(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ hasShowMoreButton: true });
        },
    },
    fields: {
        composerSuggestedRecipientViews: many('ComposerSuggestedRecipientView', {
            compute() {
                if (!this.thread) {
                    return clear();
                }
                if (this.hasShowMoreButton) {
                    return this.thread.suggestedRecipientInfoList.map(suggestedRecipientInfo => ({ suggestedRecipientInfo }));
                } else {
                    return this.thread.suggestedRecipientInfoList.slice(0, 3).map(suggestedRecipientInfo => ({ suggestedRecipientInfo }));
                }
            },
            inverse: 'composerSuggestedRecipientListViewOwner',
        }),
        composerViewOwner: one('ComposerView', {
            identifying: true,
            inverse: 'composerSuggestedRecipientListView',
        }),
        hasShowMoreButton: attr({
            default: false,
        }),
        thread: one('Thread', {
            compute() {
                return this.composerViewOwner.composer.activeThread;
            },
            required: true,
        }),
    },
});
