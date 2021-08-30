/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Returns threads that match the given search term. More specially only
        threads of model 'mail.channel' are suggested, and if the context
        thread is a private channel, only itself is returned if it matches
        the search term.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/searchSuggestions
        [Action/params]
            searchTerm
                [type]
                    String
            thread
                [type]
                    Thread
                [description]
                    prioritize and/or restrict result in the context of given thread
        [Action/returns]
            Collection
                Thread
                Thread
        [Action/behavior]
            {if}
                @thread
                .{&}
                    @thread
                    .{Thread/model}
                    .{=}
                        mail.channel
                .{&}
                    @thread
                    .{Thread/public}
                    .{!=}
                        public
            .{then}
                {Dev/comment}
                    Only return the current channel when in the context of a
                    non-public channel. Indeed, the message with the mention
                    would appear in the target channel, so this prevents from
                    inadvertently leaking the private message into the mentioned
                    channel.
                :threads
                    @thread
            .{else}
                :threads
                    {Record/all}
                        [Record/models]
                            Thread
            :cleanedSearchTerm
                {Utils/cleanSearchTerm}
                    @searchTerm
            @threads
            .{Collection/filter}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        item
                    [Function/out]
                        @item
                        .{Thread/isTemporary}
                        .{isFalsy}
                        .{&}
                            @item
                            .{Thread/model}
                            .{=}
                                mail.channel
                        .{&}
                            @item
                            .{Thread/channelType}
                            .{=}
                                channel
                        .{&}
                            @item
                            .{Thread/displayName}
                        .{&}
                            {Utils/cleanSearchTerm}
                                @thread
                                .{Thread/displayName}
                            .{String/includes}
                                @cleanedSearchTerm
`;
