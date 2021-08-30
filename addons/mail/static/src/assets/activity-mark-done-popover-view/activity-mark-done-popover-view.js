/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ActivityMarkDonePopoverView
        [Model/id]
            ActivityMarkDonePopoverView/activityViewOwner
        [Model/fields]
            activityViewOwner
            component
            feedbackTextareaRef
        [Model/actions]
            ActivityMarkDonePopoverView/_backupFeedback
            ActivityMarkDonePopoverView/_close
            ActivityMarkDonePopoverView/onBlur
            ActivityMarkDonePopoverView/onClickDiscard
            ActivityMarkDonePopoverView/onClickDone
            ActivityMarkDonePopoverView/onClickDoneAndScheduleNext
            ActivityMarkDonePopoverView/onKeydown
`;
