/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            thread
        [Element/model]
            ChatWindowComponent
        [Field/target]
            ThreadViewComponent
        [Element/isPresent]
            @record
            .{ChatWindowComponent/chatWindow}
            .{ChatWindow/threadView}
        [ThreadViewComponent/hasComposerCurrentPartnerAvatar]
            false
        [ThreadViewComponent/hasComposerSendButton]
            {Device/isMobile}
        [ThreadViewComponent/threadView]
            @record
            .{ChatWindowComponent/chatWindow}
            .{ChatWindow/threadView}
        [Element/onFocusin]
            {web.Event/stopPropagation}
                @ev
            {Record/update}
                [0]
                    @record
                    .{ChatWindowComponent/chatWindow}
                [1]
                    [ChatWindow/isFocused]
                        true
        [web.Element/style]
            [web.scss/flex]
                1
                1
                auto
            {scss/selector}
                [0]
                    .o-ThreadViewComponent-messageList
                [1]
                    [web.scss/font-size]
                        1
                        rem
`;
