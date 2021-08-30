/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            activity
        [Field/model]
            ActivityView
        [Field/type]
            one
        [Field/target]
            Activity
        [Field/isRequired]
            true
        [Field/isReadonly]
            true
        [Field/inverse]
            Activity/activityViews
`;
