/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            downloadLogsLabel
        [Element/model]
            RtcOptionListComponent
        [Record/models]
            RtcOptionListComponent/label
        [web.Element/textContent]
            {Locale/text}
                Download logs
`;
