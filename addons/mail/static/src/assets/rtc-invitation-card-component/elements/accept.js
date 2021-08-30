/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            accept
        [Element/model]
            RtcInvitationCardComponent
        [Record/models]
            RtcInvitationCardComponent/button
        [web.Element/aria-label]
            {Locale/text}
                Accept
        [web.Element/title]
            {Locale/text}
                Accept
        [Element/onClick]
            {if}
                @record
                .{RtcInvitationCardComponent/thread}
                .{Thread/hasPendingRtcRequest}
            .{then}
                {break}
            {Thread/toggleCall}
                @record
                .{RtcInvitationCardComponent/thread}
        [web.Element/style]
            [web.scss/background-color]
                {scss/theme-color}
                    success
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/background-color]
                    {scss/darken}
                        {scss/theme-color}
                            success
                        10%
`;
