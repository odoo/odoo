/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            DialogComponent]
        [web.Element/style]
            @record
            .{DialogComponent/dialog}
            .{Dialog/style}
            [web.scss/position]
                absolute
            [web.scss/top]
                0
            [web.scss/bottom]
                0
            [web.scss/left]
                0
            [web.scss/right]
                0
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            [web.scss/justify-content]
                center
            [web.scss/z-index]
                {scss/$zindex-modal}
`;
