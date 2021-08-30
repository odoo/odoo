/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Chatter/reloadParentView
        [Action/params]
            record
                [type]
                    Chatter
        [Action/behavior]
            {if}
                @record
                .{Chatter/component}
            .{then}
                {Component/trigger}
                    [0]
                        @record
                        .{Chatter/component}
                    [1]
                        reload
                    [2]
                        [keepChanges]
                            true
`;
