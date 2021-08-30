/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindowHiddenMenuComponent/_applyListHeight
        [Action/params]
            record
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                    .{ChatWindowHiddenMenuComponent/list}
                    .{web.Element/style}
                [1]
                    [web.scss/max-height]
                        {Device/globalWindowInnerHeight}
                        .{/}
                            2
                        .{+}
                            px
`;
