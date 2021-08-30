/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            settingsContent
        [Element/model]
            RtcCallViewerComponent
        [Field/target]
            RtcConfigurationMenuComponent
`;
