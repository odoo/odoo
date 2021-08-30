/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            TestTask
        [Model/fields]
            difficulty
            id
            responsible
            title
        [Model/id]
            TestTask/id
`;
