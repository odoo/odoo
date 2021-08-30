/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            rtcCallViewer
        [Field/model]
            RtcCallViewerComponent
        [Field/type]
            one
        [Field/target]
            RtcCallViewer
        [Field/isRequired]
            true
`;
