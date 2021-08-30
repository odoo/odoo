/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            activityViewOwner
        [Field/model]
            ActivityMarkDonePopoverView
        [Field/type]
            one
        [Field/target]
            ActivityView
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/inverse]
            ActivityView/activityMarkDonePopoverView
`;
