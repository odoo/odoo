/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        This value is meant to be based on field body which is
        returned by the server (and has been sanitized before stored into db).
        Do not use this value in a 't-raw' if the message has been created
        directly from user input and not from server data as it's not escaped.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            prettyBody
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{Message/body}
                .{isFalsy}
            .{then}
                {Dev/comment}
                    body null in db, body will be false instead of empty string
                {Record/empty}
                {break}
            {foreach}
                {emojis}
            .{as}
                emoji
            .{do}
                :prettyBody
                    @record
                    .{Message/body}
                    .{String/replace}
                        [0]
                            {Record/insert}
                                [Record/models]
                                    RegExp
                                [0]
                                    (?:^|\\s|<[a-z]*>)(
                                    .{+}
                                        @emoji
                                        .{Emoji/unicode}
                                    .{+}
                                        )(?=\\s|$|</[a-z]*>)
                                [1]
                                    g
                        [1]
                            <span class="o_mail_emoji">
                            .{+}
                                @emoji
                                .{Emoji/unicode}
                            .{+}
                                </span> 
                {Dev/comment}
                    Idiot-proof limit. If the user had the amazing idea of
                    copy-pasting thousands of emojis, the image rendering can lead
                    to memory overflow errors on some browsers (e.g. Chrome). Set an
                    arbitrary limit to 200 from which we simply don't replace them
                    (anyway, they are already replaced by the unicode counterpart).
                {if}
                    {String/occurences}
                        @prettyBody
                        o_mail_emoji
                    .{Collection/length}
                    .{>}
                        200
                .{then}
                    :prettyBody
                        @record
                        .{Message/body}
            {Dev/comment}
                add anchor tags to urls
            {Utils/parseAndTransform}
                [0]
                    @prettyBody
                [1]
                    addLink
`;
