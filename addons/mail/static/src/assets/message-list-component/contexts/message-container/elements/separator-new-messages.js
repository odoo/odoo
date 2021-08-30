/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            separatorNewMessages
        [Element/model]
            MessageListComponent:messageContainer
        [Record/models]
            MessageListComponent/item
            MessageListComponent/separator
        [Element/isPresent]
            @record
            .{MessageListComponent:messageContainer/messageView}
            .{MessageView/message}
            .{=}
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{ThreadView/thread}
                .{Thread/messageAfterNewMessageSeparator}
        [web.Element/class]
            @record
            .{MessageListComponent:messageContainer/transition}
            .{Transition/className}
        [web.Element/style]
            {Dev/comment}
                bug with safari: container does not auto-grow from child size
            [web.scss/padding]
                [0]
                    {scss/map-get}
                        {scss/$spacers}
                        0
                [1]
                    {scss/map-get}
                        {scss/$spacers}
                        0
            [web.scss/margin-right]
                {scss/map-get}
                    {scss/$spacers}
                    4
            [web.scss/color]
                {scss/lighten}
                    {scss/$o-brand-odoo}
                    15%
            {if}
                {Env/hasAnimation}
            .{then}
                [web.scss/transition]
                    opacity
                    0.5s
                {web.scss/selector}
                    [0]
                        &.fade-leave-to
                    [1]
                        [web.scss/opacity]
                            0
`;
