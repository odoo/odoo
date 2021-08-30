/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonIconWrapper
        [Element/model]
            RtcControllerComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/width]
                {scss/map-get}
                    {scss/$spacers}
                    4
            [web.scss/height]
                {scss/map-get}
                    {scss/$spacers}
                    4
            [web.scss/justify-content]
                center
            [web.scss/flex-direction]
                column
            [web.scss/align-items]
                center
            {if}
                @record
                .{RtcControllerComponent/rtcController}
                .{&}
                    @record
                    .{RtcControllerComponent/rtcController}
                    .{RtcController/isSmall}
            .{then}
                [web.scss/width]
                    {scss/map-get}
                        {scss/$spacers}
                        3
                [web.scss/height]
                    {scss/map-get}
                        {scss/$spacers}
                        3
`;
