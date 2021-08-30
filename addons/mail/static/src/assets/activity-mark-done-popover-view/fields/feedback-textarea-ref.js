/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            feedbackTextareaRef
        [Field/model]
            ActivityMarkDonePopoverView
        [Field/type]
            attr
        [Field/target]
            Element
        [Field/related]
            ActivityMarkDonePopoverView/component
            ActivityMarkDonePopoverComponent/feedback
`;
