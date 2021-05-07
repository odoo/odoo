/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one } from '@mail/model/model_field';
import { clear, link } from '@mail/model/model_field_command';


function factory(dependencies) {

    class SuggestionListItem extends dependencies['mail.model'] {

        /**
         * Handles click on this suggestion list item.
         *
         * @param {Event} ev
         */
        onClickSuggestion(ev) {
            ev.preventDefault();
            if (this.onSuggestionClicked) {
                this.onSuggestionClicked(this);
            }
        }

        /**
         * @private
         * @returns {mail.canned_response}
         */
        _computeCannedResponse() {
            if (this.record.constructor.modelName !== 'mail.canned_response') {
                return clear();
            }
            return link(this.record);
        }

        /**
         * @private
         * @returns {mail.thread}
         */
        _computeChannel() {
            if (this.record.constructor.modelName !== 'mail.thread') {
                return clear();
            }
            return link(this.record);
        }

        /**
         * @private
         * @returns {mail.channel_command}
         */
        _computeChannelCommand() {
            if (this.record.constructor.modelName !== 'mail.channel_command') {
                return clear();
            }
            return link(this.record);
        }

        /**
         * @private
         * @returns {string}
         */
        _computeNamePart1() {
            if (this.cannedResponse) {
                return this.cannedResponse.source;
            }
            if (this.channel) {
                return this.channel.name;
            }
            if (this.channelCommand) {
                return this.channelCommand.name;
            }
            if (this.partner) {
                return this.partner.nameOrDisplayName;
            }
            return clear();
        }

        /**
         * @private
         * @returns {string}
         */
        _computeNamePart2() {
            if (this.cannedResponse) {
                return this.cannedResponse.substitution;
            }
            if (this.channelCommand) {
                return this.channelCommand.help;
            }
            if (this.partner) {
                return _.str.sprintf(this.env._t("(%s)"), this.partner.email);
            }
            return clear();
        }

        /**
         * @private
         * @returns {mail.partner}
         */
        _computePartner() {
            if (this.record.constructor.modelName !== 'mail.partner') {
                return clear();
            }
            return link(this.record);
        }
    }

    SuggestionListItem.fields = {
        /**
         * States which canned response (if any) is the target of this suggestion list item.
         */
        cannedResponse: many2one('mail.canned_response', {
            compute: '_computeCannedResponse',
            dependencies: [
                'record',
            ],
            readonly: true,
        }),
        /**
         * Serves as compute dependency.
         */
        cannedResponseSource: attr({
            readonly: true,
            related: 'cannedResponse.source',
        }),
        /**
         * Serves as compute dependency.
         */
        cannedResponseSubstitution: attr({
            readonly: true,
            related: 'cannedResponse.substitution',
        }),
        /**
         * States which channel (if any) is the target of this suggestion list item.
         */
        channel: many2one('mail.thread', {
            compute: '_computeChannel',
            dependencies: [
                'record',
            ],
            readonly: true,
        }),
        /**
         * Serves as compute dependency.
         */
        channelName: attr({
            readonly: true,
            related: 'channel.name',
        }),
        /**
         * States which channel command (if any) is the target of this suggestion list item.
         */
        channelCommand: many2one('mail.channel_command', {
            compute: '_computeChannelCommand',
            dependencies: [
                'record',
            ],
            readonly: true,
        }),
        /**
         * Serves as compute dependency.
         */
        channelCommandHelp: attr({
            readonly: true,
            related: 'channelCommand.help',
        }),
        /**
         * Serves as compute dependency.
         */
        channelCommandName: attr({
            readonly: true,
            related: 'channelCommand.name',
        }),
        /**
         * Determines whether this suggestion list item should be highlighted.
         */
        isHighlighted: attr({
            default: false,
        }),
        /**
         * Determines whether this suggestion list item should be scrolled into
         * view at next render.
         */
        hasToScrollIntoView: attr({
            default: false,
        }),
        /**
         * States the first part of the name of this suggestion list item.
         * The name is composed of two arbitrary parts, the first one having
         * the most importance.
         */
        namePart1: attr({
            compute: '_computeNamePart1',
            dependencies: [
                'cannedResponseSource',
                'channelCommandName',
                'channelName',
                'partnerNameOrDisplayName',
            ],
            readonly: true,
        }),
        /**
         * States the second part of the name of this suggestion list item.
         * The name is composed of two arbitrary parts, the second one having
         * the least importance.
         */
        namePart2: attr({
            compute: '_computeNamePart2',
            dependencies: [
                'cannedResponseSubstitution',
                'channelCommandHelp',
                'partnerEmail',
            ],
            readonly: true,
        }),
        /**
         * Determines the function to call when this suggestion list item is
         * clicked. The function is called with one parameter, which is the
         * suggestion list item that was clicked.
         */
        onSuggestionClicked: attr(),
        /**
         * States which partner (if any) is the target of this suggestion list item.
         */
        partner: many2one('mail.partner', {
            compute: '_computePartner',
            dependencies: [
                'record',
            ],
            readonly: true,
        }),
        /**
         * Serves as compute dependency.
         */
        partnerEmail: attr({
            readonly: true,
            related: 'partner.email',
        }),
        /**
         * Serves as compute dependency.
         */
        partnerNameOrDisplayName: attr({
            readonly: true,
            related: 'partner.nameOrDisplayName',
        }),
        /**
         * Determines the record that this suggestion list item is representing.
         */
        record: many2one('mail.model', {
            required: true,
        }),
    };

    SuggestionListItem.modelName = 'mail.suggestion_list_item';

    return SuggestionListItem;
}

registerNewModel('mail.suggestion_list_item', factory);
