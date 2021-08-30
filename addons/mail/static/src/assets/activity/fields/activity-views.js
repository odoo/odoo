/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            activityViews
        [Field/model]
            Activity
        [Field/type]
            many
        [Field/target]
            ActivityView
        [Field/isCausal]
            true
        [Field/inverse]
            ActivityView/activity
`;
