/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            commandExpand
        [Element/model]
            ChatWindowHeaderComponent
        [Record/models]
            ChatWindowHeaderComponent/command
        [Element/isPresent]
            @record
            .{ChatWindowHeaderComponent/isExpandable}
        [Element/onClick]
            {web.Event/stopPropagation}
                @ev
            {ChatWindow/expand}
                @record
                .{ChatWindowHeaderComponent/chatWindow}
        [web.Element/title]
            {Locale/text}
                Open in Discuss
`;
