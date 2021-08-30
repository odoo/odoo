/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            iconOnline
        [Element/model]
            PartnerImStatusIconComponent
        [Record/models]
            PartnerImStatusIconComponent/icon
        [web.Element/class]
            fa
            fa-circle
            fa-stack-1x
        [Element/isPresent]
            @record
            .{PartnerImStatusIconComponent/partner}
            .{Partner/imStatus}
            .{=}
                online
        [web.Element/title]
            {Locale/text}
                Online
        [web.Element/role]
            img
        [web.Element/aria-label]
            {Locale/text}
                User is online
`;
