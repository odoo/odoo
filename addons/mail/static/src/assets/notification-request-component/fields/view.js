/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            view
        [Field/model]
            NotificationRequestComponent
        [Field/type]
            one
        [Field/target]
            NotificationRequestView
        [Field/isRequired]
            true
`;
