/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States if the body field is empty, regardless of editor default
        html content. To determine if a message is fully empty, use
        'isEmpty'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isBodyEmpty
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{Message/body}
            .{isFalsy}
            .{|}
                {Record/insert}
                    [Record/models]
                        Collection
                    []
                        {String/empty}
                    []
                        <p></p>
                    []
                        <p><br></p>
                    []
                        <p><br/></p>
                .{Collection/includes}
                    @record
                    .{Message/body}
                    .{String/replace}
                        []
                            /\s/g
                        []
                            ''
`;
