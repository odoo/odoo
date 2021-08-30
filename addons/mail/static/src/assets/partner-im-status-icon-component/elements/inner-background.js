/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            innerBackground
        [Element/model]
            PartnerImStatusIconComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-circle
            fa-stack-1x
        [Element/isPresent]
            @record
            .{PartnerImStatusIconComponent/partner}
            .{&}
                @record
                .{PartnerImStatusIconComponent/hasBackground}
        [web.Element/style]
            [web.scss/color]
                {scss/$white}
`;
