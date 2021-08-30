/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
            Hoverable
        [Element/name]
            selectablePartner
        [Element/model]
            ChannelInvitationFormComponent:selectablePartner
        [web.Element/class]
            d-flex
            align-items-center
            px-3
            py-1
        [Element/onClick]
            {ChannelInvitationForm/onClickSelectablePartner}
                @record
                .{ChannelInvitationFormComponent/channelInvitationForm}
                @record
                .{ChannelInvitationFormComponent:selectablePartner/selectablePartner}
        [web.Element/style]
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/background-color]
                    {scss/gray}
                        100
`;
