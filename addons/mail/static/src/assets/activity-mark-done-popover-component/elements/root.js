/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ActivityMarkDonePopoverComponent
        [Element/onKeydown]
            {ActivityMarkDonePopoverView/onKeydown}
                [0]
                    @record
                    .{ActivityMarkDonePopoverComponent/activityMarkDonePopoverView}
                [1]
                    @ev
`;
