/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            videoButton
        [Element/model]
            RtcControllerComponent
        [Record/models]
            RtcControllerComponent/button
        [web.Element/style]
            {if}
                @field
                .{RtcControllerComponent/button/isActive}
            .{then}
                [web.scss/color]
                    {scss/theme-color}
                        success
`;
