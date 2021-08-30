/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            tabLabel
        [Element/model]
            MobileMessagingNavbarComponent:tab
        [web.Element/tag]
            span
        [web.Element/textContent]
            @record
            .{MobileMessagingNavbarComponent:tab/tab}
            .{Tab/label}
        [web.Element/style]
            [web.scss/font-size]
                0.8
                em
`;
