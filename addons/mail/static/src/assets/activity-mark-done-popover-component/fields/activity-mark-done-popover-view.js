/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            activityMarkDonePopoverView
        [Field/model]
            ActivityMarkDonePopoverComponent
        [Field/type]
            one
        [Field/target]
            ActivityMarkDonePopoverView
        [Field/isRequired]
            true
        [Field/inverse]
            ActivityMarkDonePopoverView/component
`;
