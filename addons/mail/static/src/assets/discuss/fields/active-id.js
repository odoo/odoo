/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            activeId
        [Field/model]
            Discuss
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/compute]
            {if}
                @record
                .{Discuss/thread}
                .{isFalsy}
            .{then}
                {Record/empty}
            .{else}
                {Discuss/threadToActiveId}
                    [0]
                        @record
                    [1]
                        @record
                        .{Discuss/thread}
`;
