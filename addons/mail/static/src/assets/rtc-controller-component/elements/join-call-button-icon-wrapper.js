/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            joinCallButtonIconWrapper
        [Element/model]
            RtcControllerComponent
        [Record/models]
            RtcControllerComponent/buttonIconWrapper
`;
