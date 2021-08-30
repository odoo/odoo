/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            inputDeviceOption
        [Context/model]
            RtcConfigurationMenuComponent
        [Model/fields]
        [Model/template]
            inputDeviceOptionForeach
                inputDeviceOption
`;
