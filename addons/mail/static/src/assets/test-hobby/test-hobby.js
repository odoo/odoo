/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            TestHobby
        [Model/fields]
            description
        [Model/id]
            TestHobby/description
`;
