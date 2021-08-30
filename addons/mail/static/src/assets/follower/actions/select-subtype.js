/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Follower/selectSubtype
        [Action/params]
            follower
                [type]
                    Follower
            subtype
                [type]
                    FollowerSubtype
        [Action/behavior]
            {if}
                @follower
                .{Follower/selectedSubtypes}
                .{Collection/includes}
                    @subtype
                .{isFalsy}
            .{then}
                {Record/update}
                    [0]
                        @follower
                    [1]
                        [Follower/selectedSubtypes]
                            {Field/add}
                                @subtype
`;
