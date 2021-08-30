/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            partnerImStatusIcon
        [Element/model]
            ChannelMemberListMemberListComponent:member
        [Field/target]
            PartnerImStatusIconComponent
        [Element/isPresent]
            @record
            .{ChannelMemberListMemberListComponent:member/member}
            .{Partner/imStatus}
            .{!=}
                im_partner
        [web.Element/class]
            d-flex
            align-items-center
            justify-content-center
        [PartnerImStatusIconComponent/partner]
            @record
            .{ChannelMemberListMemberListComponent:member/member}
        [web.Element/style]
            {scss/include}
                {scss/o-position-absolute}
                    [$bottom]
                        0
                    [$right]
                        0
            [web.scss/color]
                {scss/theme-color}
                    light
                    {Dev/comment}
                        same as background of parent
            {if}
                {Device/isMobile}
                .{isFalsy}
            .{then}
                [web.scss/font-size]
                    x-small
`;
