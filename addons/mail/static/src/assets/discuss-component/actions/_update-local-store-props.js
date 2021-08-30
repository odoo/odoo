/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussComponent/_updateLocalStoreProps
        [Action/params]
            record
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [DiscussComponent/_lastThreadCache]
                        @record
                        .{DiscussComponent/discussView}
                        .{DiscussView/discuss}
                        .{Discuss/threadView}
                        .{&}
                            @record
                            .{DiscussComponent/discussView}
                            .{DiscussView/discuss}
                            .{Discuss/threadView}
                            .{ThreadView/threadCache}
                        .{&}
                            @record
                            .{DiscussComponent/discussView}
                            .{DiscussView/discuss}
                            .{Discuss/threadView}
                            .{ThreadView/threadCache}
                            .{Record/id}
                    [DiscussComponent/_lastThreadCounter]
                        @record
                        .{DiscussComponent/discussView}
                        .{DiscussView/discuss}
                        .{Discuss/thread}
                        .{&}
                            @record
                            .{DiscussComponent/discussView}
                            .{DiscussView/discuss}
                            .{Discuss/thread}
                            .{Thread/counter}
`;
