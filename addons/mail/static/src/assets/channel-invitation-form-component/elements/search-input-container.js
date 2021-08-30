/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            searchInputContainer
        [Element/model]
            ChannelInvitationFormComponent
        [Element/isPresent]
            {Env/isCurrentUserGuest}
            .{isFalsy}
        [web.Element/class]
            mx-3
            my-2
`;
