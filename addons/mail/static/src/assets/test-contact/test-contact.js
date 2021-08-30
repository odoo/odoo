/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            TestContact
        [Model/fields]
            address
            favorite
            hobbies
            id
            tasks
        [Model/id]
            TestContact/id
`;
