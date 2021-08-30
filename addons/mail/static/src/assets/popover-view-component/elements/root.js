/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            PopoverViewComponent
        [web.Element/style]
            [web.scss/z-index]
                {scss/$zindex-modal}
                .{+}
                    1
            [web.scss/border]
                {scss/$border-width solid}
            [web.scss/border-color]
                {scss/gray}
                    300
            [web.scss/background-color]
                {scss/$white}
            [web.scss/box-shadow]
                0
                1px
                4px
                {web.scss/rgba}
                    0
                    0
                    0
                    0.2
`;
