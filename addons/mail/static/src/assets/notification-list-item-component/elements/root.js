/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            NotificationListItemComponent
        [Record/models]
            Hoverable
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex]
                0
                0
                auto
                {Dev/comment}
                    Without this, Safari shrinks parent regardless of child content
            [web.scss/align-items]
                center
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    1
            {if}
                {Device/isMobile}
            .{then}
                [web.scss/padding]
                    {scss/map-get}
                        {scss/$spacers}
                        2
            [web.scss/cursor]
                pointer
            [web.scss/user-select]
                none
            [web.scss/background-color]
                {scss/$o-mail-notification-list-item-background-color}
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/background-color]
                    {scss/$o-mail-notification-list-item-hover-background-color}
`;
