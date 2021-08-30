/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Id of setInterval used to auto-update time elapsed of message at
        regular time.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _intervalId
        [Field/model]
            MessageViewComponent
        [Field/type]
            attr
        [Field/target]
            Number
`;
