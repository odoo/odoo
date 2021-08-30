/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            count
        [Element/model]
            MessageReactionGroupComponent
        [web.Element/tag]
            span
        [web.Element/class]
            mx-1
        [web.Element/textContent]
            @record
            .{MessageReactionGroupComponent/messageReactionGroup}
            .{MessageReactionGroup/count}
        [web.Element/style]
            {if}
                @record
                .{MessageReactionGroupComponent/messageReactionGroup}
                .{MessageReactionGroup/hasUserReacted}
            .{then}
                [web.scss/color]
                    {scss/$o-brand-primary}
                [web.scss/font-weight]
                    bold
`;
