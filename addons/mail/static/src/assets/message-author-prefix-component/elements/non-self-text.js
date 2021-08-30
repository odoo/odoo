/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            nonSelfText
        [Element/model]
            MessageAuthorPrefixComponent
        [web.Element/tag]
            span
        [Element/isPresent]
            @record
            .{MessageAuthorPrefixComponent/message}
            .{Message/author}
            .{isFalsy}
            .{|}
                @record
                .{MessageAuthorPrefixComponent/message}
                .{Message/author}
                .{&}
                    @record
                    .{MessageAuthorPrefixComponent/message}
                    .{Message/author}
                    .{!=}
                        {Env/currentPartner}
                    .{|}
                        @record
                        .{MessageAuthorPrefixComponent/message}
                        .{Message/author}
                        .{!=}
                            @record
                            .{MessageAuthorPrefixComponent/thread}
                            .{Thread/correspondent}
        [web.Element/textContent]
            {String/sprintf}
                [0]
                    {Locale/text}
                        %s:
                [1]
                    @record
                    .{MessageAuthorPrefixComponent/message}
                    .{Message/author}
                    .{Partner/nameOrDisplayName}
`;
