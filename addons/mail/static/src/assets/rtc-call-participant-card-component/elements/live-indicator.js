/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            liveIndicator
        [Element/model]
            RtcCallParticipantCardComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            {Locale/text}
                LIVE
        [web.Element/class]
            badge-pill
        [web.Element/title]
            {Locale/text}
                live
        [web.Element/aria-label]
            {Locale/text}
                live
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/margin-inline-end]
                5%
            [web.scss/align-items]
                center
            [web.scss/background-color]
                {scss/theme-color}
                    danger
            [web.scss/color]
                white
            [web.scss/user-select]
                none
            [web.scss/font-weight]
                bold
`;
