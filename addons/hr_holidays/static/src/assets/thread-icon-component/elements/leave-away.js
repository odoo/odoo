/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
            ThreadIconComponent/away
        [Element/name]
            leaveAway
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
                leave_away
        [web.Element/title]
            {Locale/text}
                Away
`;
