/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the label on the send button of this composer view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            sendButtonText
        [Field/model]
            ComposerView
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{ComposerView/composer}
                .{&}
                    @record
                    .{ComposerView/composer}
                    .{Composer/isLog}
                .{&}
                    @record
                    .{ComposerView/composer}
                    .{Composer/activeThread}
                .{&}
                    @record
                    .{ComposerView/composer}
                    .{Composer/activeThread}
                    .{Thread/model}
                    .{!=}
                        mail.channel
            .{then}
                {Locale/text}
                    Log
            .{else}
                {Locale/text}
                    Send
`;
