/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the id of this visitor.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            id
        [Field/model]
            Visitor
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
`;
