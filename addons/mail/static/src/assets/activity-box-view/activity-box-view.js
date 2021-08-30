/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ActivityBoxView
        [Model/fields]
            activityViews
            chatter
            isActivityListVisible
        [Model/id]
            ActivityBoxView/chatter
`;
