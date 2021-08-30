/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            header
        [Element/model]
            ChatWindowComponent
        [Field/target]
            ChatWindowHeaderComponent
        [ChatWindowHeaderComponent/chatWindow]
            @record
            .{ChatWindowComponent/chatWindow}
        [ChatWindowHeaderComponent/hasCloseAsBackButton]
            @record
            .{ChatWindowComponent/hasCloseAsBackButton}
        [ChatWindowHeaderComponent/isExpandable]
            @record
            .{ChatWindowComponent/isExpandable}
        [web.Element/style]
            [web.scss/flex]
                0
                0
                auto
            [web.scss/border-radius]
                3px
                3px
                0
                0
`;
