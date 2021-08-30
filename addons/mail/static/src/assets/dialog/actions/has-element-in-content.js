/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Dialog/hasElementInContent
        [Action/params]
            element
                [type]
                    web.Element
        [Action/returns]
            Boolean
        [Action/behavior]
            @record
            .{Dialog/record}
            .{&}
                {DialogRecord/containsElement}
                    [0]
                        @record
                        .{Dialog/record}
                    [1]
                        @element
`;
