/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussSidebarCategoryItem/_askAdminConfirmation
        [Action/params]
            record
                [type]
                    DiscussSidebarCategoryItem
        [Action/behavior]
            {Dialog/confirm}
                [0]
                    {Locale/text}
                        You are the administrator of this channel. Are you sure you want to leave?
                [1]
                    [buttons]
                        []
                            [text]
                                {Locale/text}
                                    Leave
                            [classes]
                                btn-primary
                            [close]
                                true
                            [click]
                                @resolve
                        []
                            [text]
                                {Locale/text}
                                    Discard
                            [close]
                                true
`;
