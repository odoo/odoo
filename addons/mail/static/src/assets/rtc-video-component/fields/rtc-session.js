/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            rtcSession
        [Field/model]
            RtcVideoComponent
        [Field/type]
            many
        [Field/target]
            RtcSession
        [Field/isRequired]
            true
`;
