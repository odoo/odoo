/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            replyingToMessage
        [Element/model]
            ComposerViewComponent
        [Element/isPresent]
            @record
            .{ComposerViewComponent/composerView}
            .{ComposerView/threadView}
            .{&}
                @record
                .{ComposerViewComponent/composerView}
                .{ComposerView/threadView}
                .{ThreadView/replyingToMessageView}
        [web.Element/textContent]
            {String/sprintf}
                [0]
                    Replying to %s
                    {if}
                        @record
                        .{ComposerViewComponent/composerView}
                        .{ComposerView/threadView}
                        .{ThreadView/thread}
                        .{!=}
                            {Env/inbox}
                    .{then}
                        %s
                [1]
                    @record
                    .{ComposerViewComponent/composerView}
                    .{ComposerView/threadView}
                    .{ThreadView/replyingToMessageView}
                    .{ReplyingToMessageView/message}
                    .{Message/authorName}
                {if}
                    @record
                    .{ComposerViewComponent/composerView}
                    .{ComposerView/threadView}
                    .{ThreadView/thread}
                    .{!=}
                        {Env/inbox}
                .{then}
                    [2]
                        {Record/insert}
                            [Record/models]
                                Element
                            [Element/name]
                                cancelReply
                            [Element/model]
                                ComposerViewComponent
                            [web.Element/tag]
                                i
                            [web.Element/class]
                                fa
                                fa-lg
                                fa-times-circle
                                rounded-circle
                                p-0
                                ml-1
                            [web.Element/title]
                                {Locale/text}
                                    Stop replying
                            [Element/onClick]
                                {ComposerView/onClickStopReplying}
                                    [0]
                                        @record
                                        .{ComposerViewComponent/composerView}
                                    [1]
                                        @ev
`;
