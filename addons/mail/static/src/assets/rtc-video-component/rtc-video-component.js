/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            RtcVideoComponent
        [Model/fields]
            rtcSession
        [Model/template]
            root
        [Model/lifecycles]
            onUpdate
`;
