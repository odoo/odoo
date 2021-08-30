/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens this thread either as form view, in discuss app, or as a chat
        window. The thread will be opened in an "active" matter, which will
        interrupt current user flow.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/open
        [Action/params]
            thread
                [type]
                    Thread
            expanded
                [type]
                    Boolean
                [default]
                    false
            focus
                [type]
                    Boolean
        [Action/behavior]
            {Dev/comment}
                check if thread must be opened in form view
            {if}
                {Record/insert}
                    [Record/models]
                        Collection
                    mail.box
                    mail.channel
                .{Collection/includes}
                    @thread
                    .{Thread/model}
                .{isFalsy}
            .{then}
                {if}
                    @expanded
                    .{|}
                        {Discuss/discussView}
                .{then}
                    {Dev/comment}
                        Close chat window because having the same thread opened
                        both in chat window and as main document does not look
                        good.
                    {ChatWindowManager/closeThread}
                        @thread
                    {Env/openDocument}
                        [id]
                            @thread
                            .{Thread/id}
                        [model]
                            @thread
                            .{Thread/model}
                    {break}
            {Dev/comment}
                check if thread must be opened in discuss
            {if}
                {Device/isMobile}
                .{isFalsy}
                .{&}
                    {Discuss/discussView}
                    .{|}
                        @expanded
                .{|}
                    @thread
                    .{Thread/model}
                    .{=}
                        mail.box
            .{then}
                {Discuss/openThread}
                    @thread
                    [focus]
                        {if}
                            @focus
                            .{!=}
                                undefined
                        .{then}
                            @focus
                        .{else}
                            {Device/isMobileDevice}
                            .{isFalsy}
            {Dev/comment}
                thread must be opened in chat window
            {ChatWindowManager/openThread}
                @thread
                [makeActive]
                    true
`;
