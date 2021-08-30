/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        timeoutId for the push to talk release delay.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _pushToTalkTimeoutId
        [Field/model]
            Rtc
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/default]
            undefined
`;
