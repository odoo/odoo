/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            callViewer
        [Field/model]
            RtcLayoutMenu
        [Field/type]
            one
        [Field/target]
            RtcCallViewer
        [Field/isReadonly]
            true
        [Field/inverse]
            RtcCallViewer/rtcLayoutMenu
`;
