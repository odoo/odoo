/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Notifies the server of new fold state. Useful for initial,
        cross-tab, and cross-device chat window state synchronization.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/notifyFoldStateToServer
        [Action/params]
            thread
                [type]
                    Thread
            state
                [type]
                    String
        [Action/behavior]
            {if}
                @thread
                .{Thread/model}
                .{!=}
                    mail.channel
            .{then}
                {Dev/comment}
                    Server sync of fold state is only supported for channels.
                {break}
            {if}
                @thread
                .{Thread/uuid}
                .{isFalsy}
            .{then}
                {break}
            {Thread/performRpcChannelFold}
                [0]
                    @thread
                    .{Thread/uuid}
                [1]
                    @state
`;
