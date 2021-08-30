/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onWillDelete
        [Lifecycle/model]
            RtcSession
        [Lifecycle/behavior]
            {RtcSession/reset}
                @record
`;
