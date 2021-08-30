/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            RtcLayoutMenuComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-direction]
                column
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    1
            [web.scss/cursor]
                pointer
            [web.scss/border-radius]
                5px
`;
