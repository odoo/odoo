/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens the most appropriate view that is a profile for this follower.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Follower/openProfile
        [Action/params]
            follower
                [type]
                    Follower
        [Action/behavior]
            {Partner/openProfile}
                @follower
                .{Follower/partner}
`;
