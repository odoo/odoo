/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            textInputContent
        [Field/model]
            Composer
        [Field/type]
            attr
        [Field/target]
            String
`;
