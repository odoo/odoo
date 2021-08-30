/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            actionReply
        [Field/model]
            MessageActionListComponent
        [Record/models]
            MessageActionListComponent/action
        [Element/isPresent]
            @record
            .{MessageActionListComponent/messageActionList}
            .{MessageActionList/hasReplyIcon}
        [web.Element/class]
            fa-reply
        [web.Element/title]
            {Locale/text}
                Reply
        [Element/onClick]
            {MessageActionList/onClickReplyTo}
                @record
                .{MessageActionListComponent/messageActionList}
`;
