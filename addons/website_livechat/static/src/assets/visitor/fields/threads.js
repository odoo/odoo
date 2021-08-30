/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Threads with this visitor as member
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threads
        [Field/model]
            Visitor
        [Field/type]
            many
        [Field/target]
            Thread
        [Field/inverse]
            Thread/visitor
`;
