/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/feature]
            snailmail
        [ModelAddon/model]
            Dialog
        [ModelAddon/id]
            @original
            .{|}
                Dialog/messageViewOwnerAsSnailmailError
        [ModelAddon/fields]
            messageViewOwnerAsSnailmailError
            snailmailErrorView
        [ModelAddon/fieldAddons]
            componentClassName
            componentName
            record
`;
