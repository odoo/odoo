/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ChatWindowHiddenMenuComponent
        [web.Element/class]
            dropup
        [web.Element/style]
            [web.scss/position]
                fixed
            [web.scss/bottom]
                0
            [web.scss/display]
                flex
            [web.scss/width]
                50
                px
            [web.scss/height]
                28
                px
            [web.scss/align-items]
                stretch
            [web.scss/background-color]
                {web.scss/gray}
                    900
            [web.scss/border-radius]
                6px
                6px
                0
                0
            [web.scss/color]
                {scss/$white}
            [web.scss/cursor]
                pointer
`;
