/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            responsible
        [Field/model]
            TestTask
        [Field/type]
            one
        [Field/target]
            TestContact
        [Field/inverse]
            TestContact/tasks
`;
