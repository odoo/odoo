/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            member
        [Element/model]
            ChannelMemberListMemberListComponent:member
        [web.Element/class]
            d-flex
            align-items-center
            mx-3
            my-1
        [web.Element/style]
            {if}
                @field
                .{web.Element/isFirst}
            .{then}
                [web.scss/margin-top]
                    {scss/map-get}
                        {scss/$spacers}
                        3
            {if}
                @field
                .{web.Element/isLast}
            .{then}
                [web.scss/margin-bottom]
                    {scss/map-get}
                        {scss/$spacers}
                        3
`;
