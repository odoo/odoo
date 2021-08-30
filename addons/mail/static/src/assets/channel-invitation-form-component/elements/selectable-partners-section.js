/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            selectablePartnersSection
        [Element/model]
            ChannelInvitationFormComponent
        [Element/isPresent]
            {Env/isCurrentUserGuest}
            .{isFalsy}
        [web.Element/class]
            d-flex
            flex-column
            flex-grow-1
            mx-0
            py-2
            overflow-auto
`;
