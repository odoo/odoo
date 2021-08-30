/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onWillUnmount
        [Lifecycle/model]
            DiscussComponent
        [Lifecycle/behavior]
            {if}
                @record
                .{DiscussComponent/discussView}
                .{DiscussView/discuss}
            .{then}
                {Discuss/close}
                    @record
                    .{DiscussComponent/discussView}
                    .{DiscussView/discuss}
`;
