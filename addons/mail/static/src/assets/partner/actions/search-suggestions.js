/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Returns partners that match the given search term.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Partner/searchSuggestions
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
            Collection<Partner>
            Collection<Partner>
        [Action/behavior]
            :isNonPublicChannel
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
            {if}
                @isNonPublicChannel
            .{then}
                {Dev/comment}
                    Only return the channel members when in the context of a
                    non-public channel. Indeed, the message with the mention
                    would be notified to the mentioned partner, so this prevents
                    from inadvertently leaking the private message to the
                    mentioned partner.
                :partners
                    @thread
                    .{Thread/members}
            .{else}
                :partners
                    {Record/all}
                        [Record/models]
                            Partner
            :cleanedSearchTerm
                {Utils/cleanSearchTerm}
                    @searchTerm
            :mainSuggestionList
                {Record/insert}
                    [Record/models]
                        Collection
            :extraSuggestionList
                {Record/insert}
                    [Record/models]
                        Collection
            {foreach}
                @partners
            .{as}
                partner
            .{do}
                {if}
                    @partner
                    .{Partner/active}
                    .{isFalsy}
                    .{&}
                        @partner
                        .{!=}
                            {Env/partnerRoot}
                    .{|}
                        @partner
                        .{Partner/id}
                        .{<=}
                            0
                    .{|}
                        {Env/publicPartners}
                        .{Collection/includes}
                            @partner
                .{then}
                    {Dev/comment}
                        ignore archived partners (except OdooBot), temporary
                        partners (livechat guests), public partners (technical)
                    {continue}
                {if}
                    @partner
                    .{Partner/nameOrDisplayName}
                    .{&}
                        {Utils/cleanSearchTerm}
                            @partner
                            .{Partner/nameOrDisplayName}
                        .{String/includes}
                            @cleanedSearchTerm
                    .{|}
                    (
                        @partner
                        .{Partner/email}
                        .{&}
                            {Utils/cleanSearchTerm}
                                @partner
                                .{Partner/email}
                            .{String/includes}
                                @cleanedSearchTerm
                .{then}
                    {if}
                        @partner
                        .{Partner/user}
                    .{then}
                        {Collection/push}
                            [0]
                                @mainSuggestionList
                            [1]
                                @partner
                    .{else}
                        {Collection/push}
                            [0]
                                @extraSuggestionList
                            [1]
                                @partner
            {Record/insert}
                [Record/models]
                    Collection
                [0]
                    @mainSuggestionList
                [1]
                    @extraSuggestionList
`;
