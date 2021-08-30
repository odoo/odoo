/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hobbies
        [Field/model]
            TestContact
        [Field/type]
            many
        [Field/target]
            TestHobby
        [Field/default]
            {Record/insert}
                []
                    [Record/models]
                        TestHobby
                    [TestHobby/description]
                        hiking
                []
                    [Record/models]
                        TestHobby
                    [TestHobby/description]
                        fishing
`;
