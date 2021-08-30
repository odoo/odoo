/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        This value is meant to be returned by the server
        (and has been sanitized before stored into db).
        Do not use this value in a 't-raw' if the message has been created
        directly from user input and not from server data as it's not escaped.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            body
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            String
`;
