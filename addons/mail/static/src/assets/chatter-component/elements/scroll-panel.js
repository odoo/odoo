/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            scrollPanel
        [Element/model]
            ChatterComponent
        [Element/onScroll]
            {Chatter/onScrollScrollPanel}
                [0]
                    @record
                    .{ChatterComponent/chatter}
                [1]
                    @ev
        [web.Element/style]
            [web.scss/overflow-y]
                auto
`;
