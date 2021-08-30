/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the index of the last "read more" that was inserted.
        Useful to remember the state for each "read more" even if their DOM
        is re-rendered.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _lastReadMoreIndex
        [Field/model]
            MessageViewComponent
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/default]
            0
`;
