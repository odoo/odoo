/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonIcon
        [Element/model]
            RtcControllerComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            {if}
                @record
                .{RtcControllerComponent/rtcController}
                .{RtcController/isSmall}
                .{isFalsy}
            .{then}
                fa-lg
`;
