/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Returns the discuss sidebar category that corresponds to this channel
        type.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/_getDiscussSidebarCategory
        [Action/params]
            record
                [type]
                    Thread
        [Action/returns]
            DiscussSidebarCategory
        [Action/behavior]
            {switch}
                @record
                .{Thread/channelType}
            .{case}
                [channel]
                    {Discuss/categoryChannel}
                [chat]
                    {Discuss/categoryChat}
                [group]
                    {Discuss/categoryChat}
`;
