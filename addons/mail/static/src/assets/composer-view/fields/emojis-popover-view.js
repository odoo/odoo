/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the emojis popover that is active on this composer view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            emojisPopoverView
        [Field/model]
            ComposerView
        [Field/type]
            one
        [Field/target]
            PopoverView
        [Field/isCausal]
            true
        [Field/inverse]
            PopoverView/composerViewOwnerAsEmoji
`;
