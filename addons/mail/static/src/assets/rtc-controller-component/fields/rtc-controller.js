/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            rtcController
        [Field/model]
            RtcControllerComponent
        [Field/type]
            one
        [Field/target]
            RtcController
        [Field/isRequired]
            true
`;
