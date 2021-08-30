/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ThreadViewTopbarComponent
        [web.Element/class]
            d-flex
            flex-shrink-0
            w-100
            px-3
        [web.Element/style]
            [web.scss/height]
                {scss/$o-statusbar-height}
                .{*}
                    1.25
            [web.scss/background-color]
                {scss/gray}
                    100
`;