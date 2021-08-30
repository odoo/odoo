/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            pttLabel
        [Element/model]
            RtcConfigurationMenuComponent
        [Record/models]
           RtcConfigurationMenuComponent/optionLabel
        [web.Element/title]
            {Locale/text}
                Use Push-to-talk
        [web.Element/aria-label]
            {Locale/text}
                Use Push-to-talk
`;
