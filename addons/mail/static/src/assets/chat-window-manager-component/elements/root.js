/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ChatWindowManagerComponent
        [web.Element/style]
            [web.scss/bottom]
                0
            [web.scss/right]
                0
            [web.scss/display]
                flex
            [web.scss/flex-direction]
                row-reverse
            [web.scss/z-index]
                1000
`;
