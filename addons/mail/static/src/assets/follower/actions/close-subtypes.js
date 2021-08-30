/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Close subtypes dialog
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Follower/closeSubtypes
        [Action/params]
            follower
                [type]
                    Follower
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [Follower/followerSubtypeListDialog]
                        {Record/empty}
`;
