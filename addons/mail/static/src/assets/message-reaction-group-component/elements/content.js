/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            content
        [Element/model]
            MessageReactionGroupComponent
        [web.Element/tag]
            span
        [web.Element/class]
            mx-1
        [web.Element/textContent]
            @record
            .{MessageReactionGroupComponent/messageReactionGroup}
            .{MessageReactionGroup/content}
`;
