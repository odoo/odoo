/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Browsing history of the visitor as a string.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            history
        [Field/model]
            Visitor
        [Field/type]
            attr
        [Field/target]
            String
`;
