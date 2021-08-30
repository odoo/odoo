/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles the click on the edit button
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ActivityView/onClickEdit
        [Action/params]
            record
                [type]
                    ActivityView
        [Action/behavior]
            {Activity/edit}
                @record
                .{ActivityView/activity}
`;
