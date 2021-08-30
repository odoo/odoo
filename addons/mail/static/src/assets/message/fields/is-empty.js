/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the message has to be considered empty or not.

        An empty message has no text, no attachment and no tracking value.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isEmpty
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {Dev/comment}
                The method does not attempt to cover all possible cases of empty
                messages, but mostly those that happen with a standard flow. Indeed
                it is preferable to be defensive and show an empty message sometimes
                instead of hiding a non-empty message.

                The main use case for when a message should become empty is for a
                message posted with only an attachment (no body) and then the
                attachment is deleted.

                The main use case for being defensive with the check is when
                receiving a message that has no textual content but has other
                meaningful HTML tags (eg. just an <img/>).
            @record
            .{Message/isBodyEmpty}
            .{&}
                @record
                .{Message/hasAttachments}
                .{isFalsy}
            .{&}
                @record
                .{Message/trackingValues}
                .{Collection/length}
                .{=}
                    0
            .{&}
                @record
                .{Message/subtypeDescription}
                .{isFalsy}
`;
