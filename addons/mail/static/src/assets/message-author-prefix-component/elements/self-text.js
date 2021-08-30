/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            selfText
        [Element/model]
            MessageAuthorPrefixComponent
        [web.Element/tag]
            span
        [Element/isPresent]
            @record
            .{MessageAuthorPrefixComponent/message}
            .{Message/author}
            .{&}
                @record
                .{MessageAuthorPrefixComponent/message}
                .{Message/author}
                .{=}
                    {Env/currentPartner}
        [web.Element/textContent]
            {Locale/text}
                You:
`;
