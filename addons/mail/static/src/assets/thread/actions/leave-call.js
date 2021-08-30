/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Notifies the server and does the cleanup of the current call.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/leaveCall
        [Action/params]
            record
                [type]
                    Thread
        [Action/behavior]
            {Thread/performLeaveCall}
                @record
`;
