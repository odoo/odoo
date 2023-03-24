/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';

import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'SuggestedRecipientInfo',
    fields: {
        composerSuggestedRecipientViews: many('ComposerSuggestedRecipientView', {
            inverse: 'suggestedRecipientInfo',
        }),
        dialogText: attr({
            compute() {
                return this.env._t("Please complete customer's information");
            },
        }),
        /**
         * Determines the email of `this`. It serves as visual clue when
         * displaying `this`, and also serves as default partner email when
         * creating a new partner from `this`.
         */
        email: attr({
            readonly: true,
        }),
        /**
         * States the id of this suggested recipient info. This id does not
         * correspond to any specific value, it is just a unique identifier
         * given by the creator of this record.
         */
        id: attr({
            identifying: true,
        }),
        /**
         * Determines whether this suggested recipient has been checked on UI.
         * A suggested recipient info is checked when current user manually set
         * checkbox to "checked" value.
         */
        isChecked: attr(),
        /**
         * Determines whether `this` will be added to recipients when posting a
         * new message on `this.thread`.
         */
        isSelected: attr({
            /**
             * Prevents selecting a recipient that does not have a partner.
             */
            compute() {
                return this.partner ? this.isChecked : false;
            },
            default: true,
        }),
        /**
         * Determines the lang of 'this'. Serves as default partner lang when
         * creating a new partner from 'this'.
         */
        lang: attr(),
        /**
         * Determines the name of `this`. It serves as visual clue when
         * displaying `this`, and also serves as default partner name when
         * creating a new partner from `this`.
         */
        name: attr({
            compute() {
                return this.partner && this.partner.nameOrDisplayName || this.name;
            },
        }),
        /**
         * Determines the optional `Partner` associated to `this`.
         */
        partner: one('Partner'),
        /**
         * Determines why `this` is a suggestion for `this.thread`. It serves as
         * visual clue when displaying `this`.
         */
        reason: attr(),
        /**
         * Determines the `Thread` concerned by `this.`
         */
        thread: one('Thread', {
            inverse: 'suggestedRecipientInfoList',
            required: true,
        }),
        titleText: attr({
            compute() {
                return sprintf(
                    this.env._t("Add as recipient and follower (reason: %s)"),
                    this.reason
                );
            },
        }),
    },
});
