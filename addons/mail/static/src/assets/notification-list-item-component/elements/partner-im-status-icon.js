/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            partnerImStatusIcon
        [Element/model]
            NotificationListItemComponent
        [web.Element/style]
            {scss/include}
                {scss/o-position-absolute}
                    [$bottom]
                        0
                    [$right]
                        0
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            [web.scss/justify-content]
                center
            [web.scss/color]
                {scss/$o-mail-notification-list-item-background-color}
            {if}
                {Device/isMobile}
                .{isFalsy}
            .{then}
                [web.scss/font-size]
                    x-small
`;
