/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            inputDeviceOptionDefault
        [Element/model]
            RtcConfigurationMenuComponent
        [web.Element/tag]
            option
        [web.Element/textContent]
            {Locale/text}
                Browser default
`;
