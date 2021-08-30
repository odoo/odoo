/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            commandCloseAsBack
        [Element/model]
            ChatWindowHeaderComponent
        [Record/models]
            ChatWindowHeaderComponent/command
            ChatWindowHeaderComponent/commandBack
            ChatWindowHeaderComponent/commandClose
        [Element/isPresent]
            @record
            .{ChatWindowHeaderComponent/hasCloseAsBackButton}
        [Element/onClick]
            {web.Event/stopPropagation}
                @ev
            {ChatWindow/close}
                @record
                .{ChatWindowHeaderComponent/chatWindow}
        [web.Element/title]
            {Locale/text}
                Close conversation
`;
