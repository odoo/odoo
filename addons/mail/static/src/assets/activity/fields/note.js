/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        This value is meant to be returned by the server
        (and has been sanitized before stored into db).
        Do not use this value in a 't-raw' if the activity has been created
        directly from user input and not from server data as it's not escaped.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            note
        [Field/model]
            Activity
        [Field/type]
            attr
        [Field/compute]
            {Dev/comment}
                Wysiwyg editor put <p><br></p> even without a note on the activity.
                This compute replaces this almost empty value by an actual empty
                value, to reduce the size the empty note takes on the UI.
            {if}
                @record
                .{Activity/note}
                .{=}
                    <p><br></p>
            .{then}
                {Record/empty}
            .{else}
                @record
                .{Activity/note}
`;
