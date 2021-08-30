/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        message.prettyBody() is inserted here from _update()
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            prettyBody
        [Element/model]
            MessageViewComponent
        [Element/isPresent]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/composerViewInEditing}
            .{isFalsy}
        [web.Element/style]
            {web.scss/selector}
                [0]
                    > p
                [1]
                    [web.scss/margin-bottom]
                        0
`;
