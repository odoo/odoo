/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
            Foreach
        [Element/name]
            selectablePartnerForeach
        [Element/model]
            ChannelInvitationFormComponent
        [Foreach/collection]
            @record
            .{ChannelInvitationFormComponent/channelInvitationForm}
            .{ChannelInvitationForm/selectablePartners}
        [Foreach/as]
            selectablePartner
        [Field/target]
            ChannelInvitationFormComponent:selectablePartner
        [ChannelInvitationFormComponent:selectablePartner/selectablePartner]
            @field
            .{Foreach/get}
                selectablePartner
        [Element/key]
            @field
            .{Foreach/get}
                selectablePartner
            .{Record/id}
`;
