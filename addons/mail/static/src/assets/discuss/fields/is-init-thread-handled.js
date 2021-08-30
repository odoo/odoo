/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines if the logic for opening a thread via the 'initActiveId'
        has been processed. This is necessary to ensure that this only
        happens once.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isInitThreadHandled
        [Field/model]
            Discuss
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
