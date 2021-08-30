/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            failureType
        [Field/model]
            Notification
        [Field/type]
            attr
`;
