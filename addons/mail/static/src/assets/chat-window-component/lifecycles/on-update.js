/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onUpdate
        [Lifecycle/model]
            ChatWindowComponent
        [Lifecycle/behavior]
            {if}
                @record
                .{ChatWindowComponent/chatWindow}
                .{isFalsy}
            .{then}
                {Dev/comment}
                    chat window is being deleted
                {break}
            {if}
                @record
                .{ChatWindowComponent/chatWindow}
                .{ChatWindow/isDoFocus}
            .{then}
                {Record/update}
                    [0]
                        @record
                        .{ChatWindowComponent/chatWindow}
                    [1]
                        [ChatWindow/isDoFocus]
                            false
                {if}
                    @record
                    .{ChatWindowComponent/newMessageFormInput}
                .{then}
                    {web.Element/focus}
                        @record
                        .{ChatWindowComponent/newMessageFormInput}
`;
