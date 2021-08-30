/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            selectablePartnerAvatar
        [Element/model]
            ChannelInvitationFormComponent:selectablePartner
        [web.Element/tag]
            img
        [web.Element/style]
            w-100
            h-100
            rounded-circle
        [web.Element/src]
            @record
            .{ChannelInvitationFormComponent:selectablePartner/selectablePartner}
            .{Partner/avatarUrl}
        [web.Element/alt]
            {Locale/text}
                Avatar
        [web.Element/style]
            [web.scss/object-fit]
                cover
`;
