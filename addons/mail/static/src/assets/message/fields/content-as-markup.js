/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            contentAsMarkup
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            Markup
        [Field/compute]
            {Record/insert}
                [Record/models]
                    Markup
                @record
                .{Message/prettyBody}
`;
