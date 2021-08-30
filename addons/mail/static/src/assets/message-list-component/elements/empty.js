/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        No result messages
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            empty
        [Element/model]
            MessageListComponent
        [Record/models]
            MessageListComponent/item
        [Element/isPresent]
            @record
            .{MessageListComponent/messageListView}
            .{MessageListView/threadViewOwner}
            .{&}
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{ThreadView/threadCache}
                .{ThreadCache/orderedNonEmptyMessages}
                .{Collection/length}
                .{=}
                    0
        [web.Element/style]
            [web.scss/flex]
                1
                1
                auto
            [web.scss/height]
                {scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/width]
                {scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/align-self]
                center
            [web.scss/display]
                flex
            [web.scss/flex-flow]
                column
            [web.scss/align-items]
                center
            [web.scss/justify-content]
                center
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    4
            [web.scss/line-height]
                2.5rem
            [web.scss/text-align]
                center
            [web.scss/font-style]
                italic
            [web.scss/color]
                {scss/$text-muted}
`;
