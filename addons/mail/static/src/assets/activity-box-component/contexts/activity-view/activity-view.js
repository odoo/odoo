/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            activityView
        [Context/model]
            ActivityBoxComponent
        [Model/fields]
            activityView
        [Model/template]
            activityViewContext
                activityView
`;
