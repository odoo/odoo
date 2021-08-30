/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            unreadCounter
        [Element/model]
            ChatWindowHiddenMenuComponent
        [web.Element/class]
            badge badge-pill
        [Element/isPresent]
            {ChatWindowManager/unreadHiddenConversationAmount}
            .{>}
                0
        [web.Element/textContent]
            {ChatWindowManager/unreadHiddenConversationAmount}
        [web.Element/style]
            [web.scss/position]
                absolute
            [web.scss/right]
                0
            [web.scss/top]
                0
            [web.scss/transform]
                {web.scss/translate}
                    50%
                    -50%
            [web.scss/z-index]
                1001
                {Dev/comment}
                    on top of bootstrap dropup menu
            [web.scss/background-color]
                {scss/$o-brand-primary}
`;
