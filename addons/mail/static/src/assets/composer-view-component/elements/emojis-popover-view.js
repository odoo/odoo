/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            emojisPopoverView
        [Element/model]
            ComposerViewComponent
        [Element/isPresent]
            @record
            .{ComposerViewComponent/composerView}
            .{ComposerView/emojisPopoverView}
        [Record/models]
            PopoverViewComponent
        [PopoverViewComponent/popoverView]
            @record
            .{ComposerViewComponent/composerView}
            .{ComposerView/emojisPopoverView}
`;
