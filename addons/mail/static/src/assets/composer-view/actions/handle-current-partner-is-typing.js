/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Called when current partner is inserting some input in composer.
        Useful to notify current partner is currently typing something in the
        composer of this thread to all other members.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerView/handleCurrentPartnerIsTyping
        [Action/params]
            record
                [type]
                    ComposerView
        [Action/behavior]
            {if}
                @record
                .{ComposerView/composer}
                .{Composer/thread}
                .{isFalsy}
            .{then}
                {Dev/comment}
                    not supported for non-thread composer (eg. messaging editing)
                {break}
            {if}
                {Env/isCurrentUserGuest}
            .{then}
                {Dev/comment}
                    not supported for guests
                {break}
            {if}
                @record
                .{ComposerView/suggestionModelName}
                .{=}
                    mail.channel_command
                .{|}
                    {ComposerView/_getCommandFromText}
                        [0]
                            @record
                        [1]
                            @record
                            .{ComposerView/composer}
                            .{Composer/textInputContent}
            .{then}
                {break}
            {if}
                @record
                .{ComposerView/composer}
                .{Composer/thread}
                .{Thread/typingMembers}
                .{Collection/includes}
                    {Env/currentPartner}
            .{then}
                {Thread/refreshCurrentPartnerIsTyping}
                    @record
                    .{ComposerView/composer}
                    .{Composer/thread}
            .{else}
                {Thread/registerCurrentPartnerIsTyping}
                    @record
                    .{ComposerView/composer}
                    .{Composer/thread}
`;
