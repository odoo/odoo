/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            loading
        [Element/model]
            MessagingMenuComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-circle-o-notch
            fa-spin
        [Element/isPresent]
            {Messaging/isInitialized}
            .{isFalsy}
        [web.Element/style]
            [web.scss/font-size]
                small
            [web.scss/position]
                absolute
            [web.scss/bottom]
                50%
            [web.scss/right]
                0
`;
