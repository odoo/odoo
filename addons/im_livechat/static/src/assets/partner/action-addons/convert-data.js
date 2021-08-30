/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/action]
            Partner/convertData
        [ActionAddon/feature]
            im_livechat
        [ActionAddon/behavior]
            :data2
                @original
            {if}
                @data
                .{Dict/hasKey}
                    livechat_username
            .{then}
                {Dev/comment}
                    flux specific, if livechat username is present it means 'name',
                    'email' and 'imStatus' contain 'false' even though their value
                    might actually exist. Remove them from data2 to avoid overwriting
                    existing value (that could be known through other means).
                {Record/update}
                    [0]
                        @data2
                    [1]
                        [Partner/name]
                            {Record/empty}
                        [Partner/email]
                            {Record/empty}
                        [Partner/imStatus]
                            {Record/empty}
                        [Partner/livechatUsername]
                            @data
                            .{Dict/get}
                                livechat_user_name
            @data2
`;
