/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Unsubscribe current user from provided channel.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/unsubscribe
        [Action/params]
            record
                [type]
                    Thread
        [Action/behavior]
            {Thread/leaveCall}
                @record
            {ChatWindowManager/closeThread}
                @record
            {Thread/unpin}
                @record
`;
