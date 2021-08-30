/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onDelete
        [Lifecycle/model]
            Thread
        [Lifecycle/behavior]
            {if}
                @record
                .{Thread/isTemporary}
            .{then}
                {foreach}
                    @record
                    .{Thread/messages}
                .{as}
                    message
                .{do}
                    {Record/delete}
                        @message
`;
