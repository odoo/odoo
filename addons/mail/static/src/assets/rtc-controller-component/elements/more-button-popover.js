/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            moreButtonPopover
        [Element/model]
            RtcControllerComponent
        [Record/models]
            PopoverComponent
        [PopoverComponent/position]
            top
`;
