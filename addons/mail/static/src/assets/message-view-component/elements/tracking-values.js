/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            trackingValues
        [Element/model]
            MessageViewComponent
        [web.Element/tag]
            ul
        [Element/isPresent]
            {MessageViewComponent/getTrackingValues}
                @record
            .{Collection/length}
            .{>}
                0
        [web.Element/style]
            [web.scss/margin-top]
                {scss/map-get}
                    {scss/$spacers}
                    2
`;
