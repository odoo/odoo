/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/feature]
            snailmail
        [Action/name]
            SnailmailErrorView/onClickFailure
        [Action/behavior]
            {if}
                @record
                .{MessageView/message}
                .{Message/type}
                .{=}
                    snailmail
            .{then}
                {Dev/comment}
                    Messages from snailmail are considered to have at most one
                    notification. The failure type of the whole message is considered
                    to be the same as the one from that first notification, and the
                    click action will depend on it.
                {switch}
                    @record
                    .{MessageView/message}
                    .{Message/notifications}
                    .{Collection/first}
                    .{Notification/failureType}
                .{then}
                    [sn_credit]
                        {Dev/comment}
                            URL only used in this component, not received at init
                        {Env/fetchSnailmailCreditsUrl}
                        {Record/update}
                            [0]
                                @record
                            [1]
                                [MessageView/snailmailErrorDialog]
                                    {Record/insert}
                                        [Record/models]
                                            Dialog
                    [sn_error]
                        {Record/update}
                            [0]
                                @record
                            [1]
                                [MessageView/snailmailErrorDialog]
                                    {Record/insert}
                                        [Record/models]
                                            Dialog
                    [sn_fields]
                        {Message/openMissingFieldsLetterAction}
                            @record
                            .{MessageView/message}
                    [sn_format]
                        {Message/openFormatLetterAction}
                            @record
                            .{MessageView/message}
                    [sn_price]
                        {Record/update}
                            [0]
                                @record
                            [1]
                                [MessageView/snailmailErrorDialog]
                                    {Record/insert}
                                        [Record/models]
                                            Dialog
                    [sn_trial]
                        {Dev/comment}
                            URL only used in this component, not received at init
                        {Env/fetchSnailmailCreditsUrlTrial}
                        {Record/update}
                            [0]
                                @record
                            [1]
                                [Messageview/snailmailErrorDialog]
                                    {Record/insert}
                                        [Record/models]
                                            Dialog
            .{else}
                @original
`;
