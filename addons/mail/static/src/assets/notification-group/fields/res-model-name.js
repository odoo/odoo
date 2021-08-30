/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            resModelName
        [Field/model]
            NotificationGroup
        [Field/type]
            attr
        [Field/target]
            String
`;
