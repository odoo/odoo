/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mobileMailboxSelection
        [Element/model]
            DiscussComponent
        [Field/target]
            DiscussMobileMailboxSelectionComponent
        [Element/isPresent]
            {Device/isMobile}
            .{&}
                {Discuss/activeMobileNavbarTabId}
                .{=}
                    mailbox
        [web.Element/class]
            border-bottom
        [web.Element/style]
            [web.scss/width]
                {scss/map-get}
                    {scss/$sizes}
                    100
`;
