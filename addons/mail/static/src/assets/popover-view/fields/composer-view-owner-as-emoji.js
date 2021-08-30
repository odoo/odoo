/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        If set, this popover view is owned by a composer view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            composerViewOwnerAsEmoji
        [Field/model]
            PopoverView
        [Field/type]
            one
        [Field/target]
            ComposerView
        [Field/isReadonly]
            true
        [Field/inverse]
            ComposerView/emojisPopoverView
`;
