/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            textInputCursorEnd
        [Field/model]
            Composer
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/default]
            0
`;
