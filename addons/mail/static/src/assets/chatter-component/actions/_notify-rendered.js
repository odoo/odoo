/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatterComponent/_notifyRendered
        [Action/params]
            record
        [Action/behavior]
            {Component/trigger}
                [0]
                    @record
                [1]
                    o-chatter-rendered
                [2]
                    [attachments]
                        @record
                        .{ChatterComponent/chatter}
                        .{Chatter/thread}
                        .{Thread/allAttachments}
                    [thread]
                        @record
                        .{ChatterComponent/chatter}
                        .{Chatter/thread}
`;
