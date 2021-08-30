/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Open the form view of the record with provided id and model.
        Gets the chat with the provided person and returns it.

        If a chat is not appropriate, a notification is displayed instead.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Env/getChat
        [Action/params]
            partnerId
            userId
        [Action/behavior]
            {if}
                @userId
            .{then}
                :user
                    {User/insert}
                        [User/id]
                            @userId
                {User/getChat}
                    @user
            .{elif}
                @partnerId
            .{then}
                :partner
                    {Record/insert}
                        [Record/models]
                            Partner
                        [Partner/id]
                            @partnerId
                {Partner/getChat}
                    @partner
`;
