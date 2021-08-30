/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            actionStar
        [Field/model]
            MessageActionListComponent
        [Record/models]
            MessageActionListComponent/action
        [Element/isPresent]
            @record
            .{MessageActionListComponent/messageActionList}
            .{MessageActionList/message}
            .{Message/canStarBeToggled}
        [web.Element/class]
            {if}
                @record
                .{MessageActionListComponent/messageActionList}
                .{MessageActionList/message}
                .{Message/isStarred}
            .{then}
                fa-star
            .{else}
                fa-star-o
        [web.Element/title]
            {Locale/text}
                Mark as Todo
        [Element/onClick]
            {MessageActionList/onClickToggleStar}
                @record
                .{MessageActionListComponent/messageActionList}
        [web.Element/style]
            {if}
                @record
                .{MessageActionListComponent/messageActionList}
                .{MessageActionList/message}
                .{Message/isStarred}
            .{then}
                [web.scss/color]
                    gold
`;
