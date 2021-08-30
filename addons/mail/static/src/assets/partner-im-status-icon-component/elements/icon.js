/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            icon
        [Element/model]
            PartnerImStatusIconComponent
        [web.Element/tag]
            i
        [web.Element/style]
            {if}
                @record
                .{PartnerImStatusIconComponent/partner}
                .{Partner/isImStatusAway}
            .{then}
                [web.scss/color]
                    {scss/theme-color}
                        warning
            {if}
                {Env/partnerRoot}
                .{=}
                    @record
                    .{PartnerImStatusIconComponent/partner}
            .{then}
                [web.scss/color]
                    {scss/$o-enterprise-primary-color}
            {if}
                @record
                .{PartnerImStatusIconComponent/partner}
                .{Partner/isImStatusOffline}
            .{then}
                [web.scss/color]
                    {scss/gray}
                        700
            {if}
                @record
                .{PartnerImStatusIconComponent/partner}
                .{Partner/isImStatusOnline}
            .{then}
                [web.scss/color]
                    {scss/$o-enterprise-primary-color}
`;
