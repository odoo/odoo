/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            selectablePartnerImStatusIcon
        [Element/model]
            ChannelInvitationFormComponent:selectablePartner
        [Element/isPresent]
            @record
            .{ChannelInvitationFormComponent:selectablePartner/selectablePartner}
            .{Partner/imStatus}
            .{&}
                @record
                .{ChannelInvitationFormComponent:selectablePartner/selectablePartner}
                .{Partner/imStatus}
                .{!=}
                    im_partner
        [Field/target]
            PartnerImStatusIconComponent
        [web.Element/class]
            d-flex
            align-items-center
            justify-content-center
            text-white
        [web.Element/style]
            {scss/include}
                {scss/o-position-absolute}
                    [$bottom]
                        0
                    [$right]
                        0
            {if}
                {Device/isMobile}
                .{isFalsy}
            .{then}
                [web.scss/font-size]
                    x-small
        [PartnerImStatusIconComponent/partner]
            @record
            .{ChannelInvitationFormComponent:selectablePartner/selectablePartner}
`;
