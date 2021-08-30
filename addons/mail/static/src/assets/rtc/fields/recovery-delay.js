/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        How long to wait before recovering a connection that has failed in ms.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            recoveryDelay
        [Field/model]
            Rtc
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/default]
            3000
`;
