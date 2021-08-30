/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            selectedPartnerLabel
        [Element/model]
            ChannelInvitationFormComponent:selectedPartner
        [web.Element/tag]
            span
        [web.Element/textContent]
            @record
            .{ChannelInvitationFormComponent:selectedPartner/selectedPartner}
            .{Partner/nameOrDisplayName}
`;
