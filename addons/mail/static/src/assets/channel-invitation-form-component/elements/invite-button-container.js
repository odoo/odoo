/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            inviteButtonContainer
        [Element/model]
            ChannelInvitationFormComponent
        [Element/isPresent]
            {Env/isCurrentUserGuest}
            .{isFalsy}
        [web.Element/class]
            mx-3
            mt-2
            mb-3
`;
