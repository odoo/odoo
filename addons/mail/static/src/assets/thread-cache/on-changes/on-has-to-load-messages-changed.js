/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Loads initial messages from 'this'.
        This is used to trigger the load of messages at the right time.
    {onChange}
        [onChange/name]
            onHasToLoadMessagesChanged
        [onChange/model]
            ThreadCache
        [onChange/dependencies]
            ThreadCache/hasToLoadMessages
        [onChange/compute]
            {Dev/comment}
                Loads this thread cache, by fetching the most recent messages in this
                conversation.
            {if}
                @record
                .{ThreadCache/hasToLoadMessages}
            .{then}
                :fetchedMessages
                    {ThreadCache/_loadMessages}
                        @record
                {foreach}
                    @record
                    .{ThreadCache/threadViews}
                .{as}
                    threadView
                .{do}
                    {ThreadView/addComponentHint}
                        [0]
                            @threadView
                        [1]
                            messages-loaded
                        [2]
                            [fetchedMessages]
                                @fetchedMessages
`;
