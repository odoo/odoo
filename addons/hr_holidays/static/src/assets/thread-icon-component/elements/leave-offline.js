/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
            ThreadIconComponent/offline
        [Element/name]
            leaveOffline
        [Element/feature]
            hr_holidays
        [Element/model]
            ThreadIconComponent
        [web.Element/class]
            fa
            fa-plane
        [Element/isPresent]
            @record
            .{ThreadIconComponent/thread}
            .{Thread/correspondent}
            .{Partner/imStatus}
            .{=}
                leave_offline
        [web.Element/title]
            {Locale/text}
                Out of office
`;
