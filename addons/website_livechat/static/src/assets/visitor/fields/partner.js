/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Partner linked to this visitor, if any.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            partner
        [Field/model]
            Visitor
        [Field/type]
            one
        [Field/target]
            Partner
`;
