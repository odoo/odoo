/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Value of the last rendered prettyBody. Useful to compare to new value
        to decide if it has to be updated.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _lastPrettyBody
        [Field/model]
            MessageViewComponent
        [Field/type]
            attr
        [Field/target]
            String
`;
