/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadCacheInitialScrollHeight
        [Field/model]
            ThreadView
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/compute]
            {if}
                @record
                .{ThreadView/threadCache}
                .{isFalsy}
            .{then}
                {Record/empty}
                {break}
            :threadCacheInitialScrollHeight
                @record
                .{ThreadView/threadCacheInitialScrollHeights}
                .{Record/get}
                    @record
                    .{ThreadView/threadCache}
                    .{Record/id}
            {if}
                @threadCacheInitialScrollHeight
                .{!=}
                    undefined
            .{then}
                @threadCacheInitialScrollHeight
            .{else}
                {Record/empty}
`;
