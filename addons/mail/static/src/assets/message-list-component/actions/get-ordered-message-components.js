/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Get list of sub-components Message, ordered based on prop 'order'
        (ASC/DESC).

        The asynchronous nature of OWL rendering pipeline may reveal disparity
        between knowledgeable state of store between components. Use this getter
        with extreme caution!

        Let's illustrate the disparity with a small example:

        - Suppose this component is aware of ordered (record) messages with
        following IDs: [1, 2, 3, 4, 5], and each (sub-component) messages map
        each of these records.
        - Now let's assume a change in store that translate to ordered (record)
        messages with following IDs: [2, 3, 4, 5, 6].
        - Because store changes trigger component re-rendering by their "depth"
        (i.e. from parents to children), this component may be aware of
        [2, 3, 4, 5, 6] but not yet sub-components, so that some (component)
        messages should be destroyed but aren't yet (the ref with message ID 1)
        and some do not exist yet (no ref with message ID 6).
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageListComponent/getOrderedMessageViewComponents
        [Action/params]
            record
                [type]
                    MessageListComponent
        [Action/returns]
            Collection<MessageViewComponent>
        [Action/behavior]
            :ascOrderedMessageRefs
                @record
                .{MessageListComponent/messages}
                .{Collection/sort}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            item1
                            item2
                        [Function/out]
                            {if}
                                @item1
                                .{MessageViewComponent/message}
                                .{Message/id}
                                .{<}
                                    @item2
                                    .{MessageViewComponent/message}
                                    .{Message/id}
                            .{then}
                                -1
                            .{else}
                                1
            {if}
                @record
                .{MessageListComponent/order}
                .{=}
                    desc
            .{then}
                @ascOrderedMessageRefs
                .{Collection/reverse}
            .{else}
                @ascOrderedMessageRefs
`;
