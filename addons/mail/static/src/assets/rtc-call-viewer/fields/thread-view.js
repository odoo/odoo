/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        ThreadView on which the call viewer is attached.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadView
        [Field/model]
            RtcCallViewer
        [Field/type]
            one
        [Field/target]
            ThreadView
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/inverse]
            ThreadView/rtcCallViewer
`;
