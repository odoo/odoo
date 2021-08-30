/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            inputDeviceLabel
        [Element/model]
            RtcConfigurationMenuComponent
        [Record/models]
            RtcConfigurationMenuComponent/optionLabel
        [web.Element/title]
            {Locale/text}
                Input device
        [web.Element/aria-label]
            {Locale/text}
                Input device
`;
