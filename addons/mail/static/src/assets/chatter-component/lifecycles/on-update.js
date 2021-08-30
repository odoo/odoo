/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onUpdate
        [Lifecycle/model]
            ChatterComponent
        [Lifecycle/behavior]
            {if}
                @record
                .{ChatterComponent/chatter}
                .{isFalsy}
            .{then}
                {break}
            {if}
                @record
                .{ChatterComponent/chatter}
                .{Chatter/thread}
            .{then}
                {ChatterComponent/_notifyRendered}
                    @record
`;
