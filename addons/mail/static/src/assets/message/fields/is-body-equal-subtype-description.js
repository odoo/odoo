/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether 'body' and 'subtype_description' contain similar
        values.

        This is necessary to avoid displaying both of them together when they
        contain duplicate information. This will especially happen with
        messages that are posted automatically at the creation of a record
        (messages that serve as tracking messages). They do have hard-coded
        "record created" body while being assigned a subtype with a
        description that states the same information.

        Fixing newer messages is possible by not assigning them a duplicate
        body content, but the check here is still necessary to handle
        existing messages.

        Limitations:
        - A translated subtype description might not match a non-translatable
        body created by a user with a different language.
        - Their content might be mostly but not exactly the same.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isBodyEqualSubtypeDescription
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            {if}
                @record
                .{Message/body}
                .{isFalsy}
                .{|}
                    @record
                    .{Message/subtypeDescription}
                    .{isFalsy}
            .{then}
                false
            .{else}
                {Utils/htmlToTextContentInline}
                    @record
                    .{Message/body}
                .{String/toLowerCase}
                .{=}
                    @record
                    .{Message/subtypeDescription}
                    .{String/toLowerCase}
`;
