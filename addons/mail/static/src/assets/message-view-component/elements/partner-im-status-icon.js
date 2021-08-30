/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            partnerImStatusIcon
        [Element/model]
            MessageViewComponent
        [Field/target]
            PartnerImStatusIconComponent
        [PartnerImStatusIconComponent/hasOpenChat]
            @record
            .{MessageViewComponent/hasAuthorOpenChat}
        [PartnerImStatusIconComponent/partner]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/message}
            .{Message/author}
        [Element/isPresent]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/message}
            .{Message/author}
            .{&}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/author}
                .{Partner/imStatus}
        [web.Element/style]
            {web.scss/include}
                {web.scss/o-position-absolute}
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
                {scss/$white}
            {if}
                {Device/isMobile}
                .{isFalsy}
            .{then}
                [web.scss/font-size]
                    x-small
`;
