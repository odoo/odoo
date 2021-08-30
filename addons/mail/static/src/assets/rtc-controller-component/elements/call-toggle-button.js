/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            callToggleButton
        [Element/model]
            RtcControllerComponent
        [Record/models]
            RtcControllerComponent/button
        [web.Element/style]
            [web.scss/background-color]
                {web.scss/theme-color}
                    success
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/background-color]
                    {scss/darken}
                        {scss/theme-color}
                            success
                        20%
            {if}
                @field
                .{RtcControllerComponent/button/isActive}
            .{then}
                [web.scss/background-color]
                    {scss/theme-color}
                        danger
                {if}
                    @field
                    .{web.Element/isHover}
                .{then}
                    [web.scss/background-color]
                        {scss/darken}
                            {scss/theme-color}
                                danger
                            20%
`;
