/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Hides the composer, which only makes sense if the composer is
        currently used as a Discuss Inbox reply composer or as message
        editing.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerView/discard
        [Action/params]
            record
                [type]
                    ComposerView
        [Action/behavior]
            {if}
                @record
                .{ComposerView/messageViewInEditing}
            .{then}
                {MessageView/stopEditing}
                    @record
                    .{ComposerView/messageViewInEditing}
            {if}
                @record
                .{ComposerView/threadView}
                .{&}
                    @record
                    .{ComposerView/threadView}
                    .{ThreadView/replyingToMessageView}
            .{then}
                {if}
                    @record
                    .{ComposerView/threadView}
                    .{ThreadView/thread}
                    .{=}
                        {Env/inbox}
                .{then}
                    {Record/delete}
                        @record
                {Record/update}
                    [0]
                        @record
                        .{ComposerView/threadView}
                    [1]
                        [ThreadView/replyingToMessageView]
                            {Record/empty}
`;
