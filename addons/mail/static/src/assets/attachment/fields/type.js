/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            type
        [Field/model]
            Attachment
        [Field/type]
            attr
`;
