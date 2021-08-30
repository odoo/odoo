/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            downloadLogsIcon
        [Element/model]
            RtcOptionListComponent
        [Record/models]
            RtcOptionListComponent/icon
        [web.Element/class]
            fa-text-o
`;
