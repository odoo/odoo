/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Get the current partner image URL.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerViewComponent/getCurrentPartnerAvatar
        [Action/behavior]
            {if}
                {Env/currentUser}
                .{isFalsy}
            .{then}
                /web/static/img/user_menu_avatar.png
            .{else}
                @env
                .{Env/owlEnv}
                .{Dict/get}
                    session
                .{Dict/get}
                    url
                .{Function/call}
                    [0]
                        /web/image
                    [1]
                        [field]
                            avatar_128
                        [id]
                            {Env/currentUser}
                            .{User/id}
                        [model]
                            res.users
`;
