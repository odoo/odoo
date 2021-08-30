/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ActivityView
        [Model/fields]
            activity
            activityBoxView
            activityMarkDonePopoverView
            areDetailsVisible
            assignedUserText
            delayLabel
            fileUploader
            formattedCreateDatetime
            formattedDeadlineDate
            markDoneText
            summary
        [Model/id]
            ActivityView/activityBoxView
            .{&}
                ActivityView/activity
        [Model/actions]
            ActivityView/onClickActivity
            ActivityView/onClickCancel
            ActivityView/onClickDetailsButton
            ActivityView/onClickEdit
            ActivityView/onClickUploadDocument
`;
