/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Discuss/threadToActiveId
        [Action/params]
            discuss
            thread
        [Action/behavior]
            @thread
            .{Thread/model}
            .{+}
                _
            .{+}
                @thread
                .{Thread/id}
`;
