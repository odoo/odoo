/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Notify server to leave the current channel. Useful for cross-tab
        and cross-device chat window state synchronization.

        Only makes sense if isPendingPinned is set to the desired value.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/notifyPinStateToServer
        [Action/params]
            thread
                [type]
                    Thread
        [Action/behavior]
            {if}
                @thread
                .{Thread/isPendingPinned}
            .{then}
                {Thread/performRpcChannelPin}
                    [pinned]
                        true
                    [uuid]
                        @thread
                        .{Thread/uuid}
            .{else}
                {Thread/performRpcExecuteCommand}
                    [channelId]
                        @thread
                        .{Thread/id}
                    [command]
                        leave
`;
