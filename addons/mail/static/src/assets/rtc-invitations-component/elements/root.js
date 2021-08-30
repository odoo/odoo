/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            RtcInvitationsComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-direction]
                column
            [web.scss/position]
                absolute
            [web.scss/top]
                0px
            [web.scss/right]
                0px
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/z-index]
                {scss/$zindex-modal}
`;
