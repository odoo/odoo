/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            textInputCursorStart
        [Field/model]
            Composer
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/default]
            0
`;
