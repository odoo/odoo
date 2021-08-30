/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatterContainerComponent/_insertFromProps
        [Action/params]
            props
            record
        [Action/behavior]
            :values
                {Record/insert}
                    [Record/models]
                        Chatter
                    @props
                    [Chatter/id]
                        @record
                        .{ChatterContainerComponent/_chatterId}
            {if}
                @values
                .{Chatter/threadId}
                .{=}
                    undefined
            .{then}
                {Record/update}
                    [0]
                        @values
                    [1]
                        [Chatter/threadId]
                            {Record/empty}
            {Record/update}
                [0]
                    @record
                [1]
                    [ChatterContainerComponent/chatter]
                        @values
            {Dev/comment}
                Refresh the chatter when the parent view is (re)loaded.
                This serves mainly at loading initial data, but also on reload there
                might be new message, new attachment, ...

                For example in approvals this is currently necessary to fetch the
                newly added attachment when using the "Attach Document" button. And
                in sales it is necessary to see the email when using the "Send email"
                button.

                NOTE: this assumes props are actually changed when a reload of parent
                happens which is true so far because of the OWL compatibility layer
                calling the props change method but it is in general not a good
                assumption to make.
            {Chatter/refresh}
                @record
                .{ChatterContainerComponent/chatter}
            {Component/render}
                @record
`;
