/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The model for the controller (buttons).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            rtcController
        [Field/model]
            RtcCallViewer
        [Field/type]
            one
        [Field/target]
            RtcController
        [Field/isReadonly]
            true
        [Field/isCausal]
            true
        [Field/inverse]
            RtcController/callViewer
        [Field/default]
            {Record/insert}
                [Record/models]
                    RtcController
`;
