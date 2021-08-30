/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Executes the given async function, only when the last function
        executed by this method terminates. If there is already a pending
        function it is replaced by the new one. This ensures the result of
        these function come in the same order as the call order, and it also
        allows to skip obsolete intermediate calls.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerView/_executeOrQueueFunction
        [Action/params]
            record
                [type]
                    ComposerView
            func
                [type]
                    Function
        [Action/behavior]
            {if}
                @record
                .{ComposerView/_hasMentionRpcInProgress}
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [ComposerView/_nextMentionRpcFunction]
                            @func
                {break}
            {Record/update}
                [0]
                    @record
                [1]
                    [ComposerView/_hasMentionRpcInProgress]
                        true
                    [ComposerView/_nextMentionRpcFunction]
                        {Record/empty}
            {Promise/await}
                @func
                .{Function/call}
            {if}
                {Record/exists}
                    @record
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [ComposerView/_hasMentionRpcInProgress]
                            false
                {if}
                    @record
                    .{ComposerView/_nextMentionRpcFunction}
                .{then}
                    {ComposerView/_executeOrQueueFunction}
                        [0]
                            @record
                        [1]
                            @record
                            .{ComposerView/_nextMentionRpcFunction}
`;
