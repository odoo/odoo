/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            outOfOffice
        [Element/feature]
            hr_holidays
        [Element/model]
            ThreadViewComponent
        [web.Element/class]
            alert
            alert-primary
        [Element/isPresent]
            @record
            .{ThreadViewComponent/threadView}
            .{ThreadView/thread}
            .{Thread/correspondent}
            .{&}
                @record
                .{ThreadViewComponent/threadView}
                .{ThreadView/thread}
                .{Thread/correspondent}
                .{Partner/outOfOfficeText}
        [web.Element/role]
            alert
        [web.Element/textContent]
            @record
            .{ThreadViewComponent/threadView}
            .{ThreadView/thread}
            .{Thread/correspondent}
            .{Partner/outOfOfficeText}
        [web.Element/style]
            [web.scss/margin-top]
                0
            [web.scss/margin-bottom]
                0
`;
