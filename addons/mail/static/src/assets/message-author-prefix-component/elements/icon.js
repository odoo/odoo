/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Elememt/name]
            icon
        [Element/model]
            MessageAuthorPrefixComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-mail-reply
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
        [web.Element/style]
            [web.scss/margin-right]
                {scss/map-get}
                    {scss/$spacers}
                    1
`;
