/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _timeoutId
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/default]
            undefined
`;
