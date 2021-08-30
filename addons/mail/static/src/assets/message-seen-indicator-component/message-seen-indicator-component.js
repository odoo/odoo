/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MessageSeenIndicatorComponent
        [Model/fields]
            message
            messageSeenIndicator
            thread
        [Model/template]
            root
                icon1
                icon2
`;
