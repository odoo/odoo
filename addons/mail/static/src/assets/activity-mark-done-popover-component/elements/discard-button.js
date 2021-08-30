/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            discardButton
        [Element/model]
            ActivityMarkDonePopoverComponent
        [web.Element/tag]
            button
        [web.Element/type]
            button
        [web.Element/class]
            btn
            btn-sm
            btn-link
        [Element/onClick]
            {ActivityMarkDonePopoverView/onClickDiscard}
                [0]
                    @record
                    .{ActivityMarkDonePopoverComponent/activityMarkDonePopoverView}
                [1]
                    @ev
        [web.Element/textContent]
            {Locale/text}
                Discard
`;
