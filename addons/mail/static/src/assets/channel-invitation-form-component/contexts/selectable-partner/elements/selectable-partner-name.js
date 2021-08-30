/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            selectablePartnerName
        [Element/model]
            ChannelInvitationFormComponent:selectablePartner
        [web.Element/tag]
            span
        [web.Element/class]
            flex-grow-1
            text-truncate
        [web.Element/textContent]
            @record
            .{ChannelInvitationFormComponent:selectablePartner/selectablePartner}
            .{Partner/nameOrDisplayName}
        [web.Element/style]
            [web.scss/min-width]
                0
`;
