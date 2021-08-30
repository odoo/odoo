/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onUpdate
        [Lifecycle/model]
            ChatterContainerComponent
        [Lifecycle/behavior]
            {if}
                @record
                .{ChatterContainerComponent/chatter}
                .{isFalsy}
            .{then}
                {break}
            {Chatter/refresh}
                @record
                .{ChatterContainerComponent/chatter}
`;
