/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
            PartnerImStatusIconComponent/icon
        [Element/name]
            iconLeaveAway
        [Element/model]
            PartnerImStatusIconComponent
        [Element/feature]
            hr_holidays
        [web.Element/class]
            fa
            fa-plane
            fa-stack-1x
        [Element/isPresent]
            @record
            .{PartnerImStatusIconComponent/partner}
            .{Partner/imStatus}
            .{=}
                leave_away
        [web.Element/title]
            {Locale/text}
                Away
        [web.Element/role]
            img
        [web.Element/aria-label]
            {Locale/text}
                User is away
`;
