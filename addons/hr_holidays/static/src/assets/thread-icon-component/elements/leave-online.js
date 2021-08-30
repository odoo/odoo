/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
            ThreadIconComponent/online
        [Element/name]
            leaveOnline
        [Element/feature]
            hr_holidays
        [Element/model]
            ThreadIconComponent
        [Element/isPresent]
            @record
            .{ThreadIconComponent/thread}
            .{Thread/correspondent}
            .{Partner/imStatus}
            .{=}
                leave_online
        [web.Element/title]
            {Locale/text}
                Online
`;
