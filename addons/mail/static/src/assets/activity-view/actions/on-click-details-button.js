/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles the click on the detail button
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ActivityView/onClickDetailsButton
        [Action/params]
            record
                [type]
                    ActivityView
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [ActivityView/areDetailsVisible]
                        @record
                        .{ActivityView/areDetailsVisible}
                        .{isFalsy}
`;
