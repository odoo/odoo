/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Returns whether the given html element is inside this snailmail error view.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            SnailmailErrorView/containsElement
        [Action/params]
            element
                [type]
                    web.Element
            record
                [type]
                    SnailmailErrorView
        [Action/returns]
            Boolean
        [Action/behavior]
            @record
            .{SmailmailErrorView/component}
            .{&}
                @record
                .{SnailmailErrorView/component}
                .{SnailmailErrorComponent/contains}
                    @element
`;
