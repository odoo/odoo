/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            actionDelete
        [Field/model]
            MessageActionListComponent
        [Record/models]
            MessageActionListComponent/action
        [Element/isPresent]
            @record
            .{MessageActionListComponent/messageActionList}
            .{MessageActionList/message}
            .{Message/canBeDeleted}
        [web.Element/class]
            fa-trash
        [web.Element/title]
            {Locale/text}
                Delete
        [Element/onClick]
            {MessageActionList/onClickDelete}
                @record
                .{MessageActionListComponent/messageActionList}
`;
