/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mobileNewChatButton
        [Element/model]
            DiscussComponent
        [web.Element/tag]
            button
        [Field/class]
            btn
            btn-secondary
        [Element/isPresent]
            {Device/isMobile}
            .{&}
                {Discuss/activeMobileNavbarTabId}
                .{=}
                    chat
        [Element/onClick]
            {Discuss/onClickMobileNewChatButton}
                @ev
        [web.Element/textContent]
            {Locale/text}
                Start a conversation
`;
