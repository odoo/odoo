/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States if the attachment is a text file.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isText
        [Field/model]
            Attachment
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {Record/insert}
                [Record/models]
                    Collection
                application/javascript
                application/json
                text/css
                text/html
                text/plain
            .{Collection/includes}
                @record
                .{Attachment/mimetype}
`;
