/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            header
        [Element/model]
            MessageViewComponent
        [Element/isPresent]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/isSquashed}
            .{isFalsy}
        [web.Element/class]
            ml-2
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-flow]
                row
                wrap
            [web.scss/align-items]
                baseline
`;
