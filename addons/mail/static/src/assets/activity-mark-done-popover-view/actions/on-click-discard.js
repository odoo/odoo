/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on this "Discard" button.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ActivityMarkDonePopoverView/onClickDiscard
        [Action/params]
            record
                [type]
                    ActivityMarkDonePopoverView
        [Action/behavior]
            {ActivityMarkDonePopoverView/_close}
                @record
`;
