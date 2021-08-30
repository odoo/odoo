/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            tabIcon
        [Element/model]
            MobileMessagingNavbarComponent:tab
        [web.Element/tag]
            span
        [Element/isPresent]
            @record
            .{MobileMessagingNavbarComponent:tab/tab}
            .{Tab/icon}
        [web.Element/class]
            @record
            .{MobileMessagingNavbarComponent:tab/tab}
            .{Tab/icon}
        [web.Element/style]
            [web.scss/margin-bottom]
                4%
            [web.scss/font-size]
                1.3
                em
`;
