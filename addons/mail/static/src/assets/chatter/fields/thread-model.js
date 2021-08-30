/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the model of the thread that will be displayed by 'this'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadModel
        [Field/model]
            Chatter
        [Field/type]
            attr
        [Field/target]
            String
`;
