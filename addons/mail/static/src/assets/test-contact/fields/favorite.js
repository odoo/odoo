/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            favorite
        [Field/model]
            TestContact
        [Field/type]
            one
        [Field/target]
            TestHobby
        [Field/default]
            {Record/insert}
                [Record/models]
                    TestHobby
                [TestHobby/description]
                    football
`;
