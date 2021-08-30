/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            authorAvatarContainer
        [Element/model]
            MessageViewComponent
        [Record/models]
            MessageViewComponent/sidebarItem
        [Element/isPresent]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/isSquashed}
            .{isFalsy}
        [web.Element/style]
            [web.scss/position]
                relative
            [web.scss/height]
                36
                px
            [web.scss/width]
                36
                px
`;
