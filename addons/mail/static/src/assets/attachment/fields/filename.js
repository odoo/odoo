/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            filename
        [Field/model]
            Attachment
        [Field/type]
            attr
        [Field/target]
            String
`;
