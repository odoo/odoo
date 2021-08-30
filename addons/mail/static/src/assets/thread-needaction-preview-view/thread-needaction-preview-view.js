/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ThreadNeedactionPreviewView
        [Model/id]
            ThreadNeedactionPreviewView/notificationListViewOwner
            .{&}
                ThreadNeedactionPreviewView/thread
        [Model/fields]
            notificationListViewOwner
            thread
`;
