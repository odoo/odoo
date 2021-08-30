/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the date of the message as a moment object.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            date
        [Field/model]
            Message
        [Field/type]
            attr
`;
