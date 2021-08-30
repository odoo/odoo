/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            url
        [Field/model]
            Attachment
        [Field/type]
            attr
        [Field/target]
            String
`;
