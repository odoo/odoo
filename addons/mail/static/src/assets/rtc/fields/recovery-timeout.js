/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        How long to wait before considering a connection as needing recovery in ms.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            recoveryTimeout
        [Field/model]
            Rtc
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/default]
            15000
`;
