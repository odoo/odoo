/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            PartnerImStatusIconComponent
        [web.Element/tag]
            span
        [web.Element/class]
            fa-stack
        [Element/onClick]
            {if}
                @record
                .{PartnerImStatusIconComponent/hasOpenChat}
            .{then}
                {Partner/openChat}
                    @record
                    .{PartnerImStatusIconComponent/partner}
        [web.Element/data-partner-local-id]
            @record
            .{PartnerImStatusIconComponent/partner}
            .{Record/id}
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-flow]
                column
            [web.scss/width]
                1.2
                em
            [web.scss/height]
                1.2
                em
            [web.scss/line-height]
                1.3
                em
            {if}
                @record
                .{PartnerImStatusIconComponent/hasOpenChat}
            .{then}
                [web.scss/cursor]
                    pointer
`;
