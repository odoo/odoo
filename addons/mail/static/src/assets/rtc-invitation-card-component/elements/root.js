/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            RtcInvitationCardComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-direction]
                column
            [web.scss/margin]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    5
            [web.scss/border-radius]
                3px
            [web.scss/background-color]
                {scss/gray}
                    900
            [web.scss/border]
                1px
                solid
                black
`;
