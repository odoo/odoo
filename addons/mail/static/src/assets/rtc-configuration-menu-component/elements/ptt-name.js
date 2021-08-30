/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            pttName
        [Element/model]
            RtcConfigurationMenuComponent
        [Record/models]
           RtcConfigurationMenuComponent/optionName
        [web.Element/textContent]
            {Locale/text}
                Use Push-to-talk
`;
