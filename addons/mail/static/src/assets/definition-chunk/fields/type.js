/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        either of these types:
            - call 1
            - call 2
            - entry
            - set
            - read
            - text
            - noop
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            type
        [Field/model]
            DefinitionChunk
        [Field/type]
            attr
        [Field/target]
            String
`;
