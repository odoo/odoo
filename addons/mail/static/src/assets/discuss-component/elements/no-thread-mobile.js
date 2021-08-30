/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            noThreadMobile
        [Element/model]
            DiscussComponent
        [Record/models]
            DiscussComponent/noThread
        [Element/isPresent]
            {Device/isMobile}
            .{&}
                {Discuss/thread}
                .{isFalsy}
            .{&}
                {Discuss/activeMobileNavbarTabId}
                .{=}
                    mailbox
        [web.Element/textContent]
            {Locale/text}
                No conversation selected.
`;
