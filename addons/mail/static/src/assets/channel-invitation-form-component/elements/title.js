/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            title
        [Element/model]
            ChannelInvitationFormComponent
        [web.Element/tag]
            h3
        [web.Element/class]
            mx-3
            mt-3
            mb-2
        [web.Element/textContent]
            {Locale/text}
                Invite people
`;
