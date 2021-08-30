/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussSidebarCategoryItem/_askLeaveGroupConfirmation
        [Action/params]
            record
                [type]
                    DiscussSidebarCategoryItem
        [Action/behavior]
            {Dialog/confirm}
                []
                    {Locale/text}
                        You are about to leave this group conversation and will no longer have access to it unless you are invited again. Are you sure you want to continue?
                []
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
                                resolve
                        []
                            [text]
                                {Locale/text}
                                    Discard
                            [close]
                                true
`;
