/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            Device
        [Model/fields]
            globalWindowInnerHeight
            globalWindowInnerWidth
            isMobile
            isMobileDevice
            sizeClass
        [Model/id]
            Device/messaging
        [Model/actions]
            Device/_refresh
            Device/start
            Device/stop
`;
