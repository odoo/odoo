/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            activityBoxView
        [Field/model]
            ActivityBoxComponent
        [Field/type]
            one
        [Field/target]
            ActivityBoxView
        [Field/isRequired]
            true
`;
