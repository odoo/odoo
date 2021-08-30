/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the message that this message replies to (if any). Only makes
        sense on channels. Other types of threads might have a parent message
        (parent_id in python) that should be ignored for the purpose of this
        feature.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            parentMessage
        [Field/model]
            Message
        [Field/type]
            one
        [Field/target]
            Message
`;
