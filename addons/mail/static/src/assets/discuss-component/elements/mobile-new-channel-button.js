/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mobileNewChannelButton
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
                    channel
        [Element/onClick]
            {Discuss/onClickMobileNewChannelButton}
                @ev
        [web.Element/textContent]
            {Locale/text}
                New Channel
`;
