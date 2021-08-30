/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Unpin this thread and notify server of the change.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/unpin
        [Action/params]
            thread
                [type]
                    Thread
        [Action/behavior]
            {Record/update}
                [0]
                    @thread
                [1]
                    [Thread/isPendingPinned]
                        false
            {Thread/notifyPinStateToServer}
                @thread
`;
