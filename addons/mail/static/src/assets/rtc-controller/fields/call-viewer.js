/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            callViewer
        [Field/model]
            RtcController
        [Field/type]
            one
        [Field/target]
            RtcCallViewer
        [Field/inverse]
            RtcCallViewer/rtcController
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
`;
