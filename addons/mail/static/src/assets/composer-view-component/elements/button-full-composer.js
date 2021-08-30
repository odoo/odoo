/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonFullComposer
        [Element/model]
            ComposerViewComponent
        [web.Element/tag]
            button
        [Record/models]
            ComposerViewComponent/button
            ComposerViewComponent/toolButton
        [web.Element/class]
            btn
            btn-light
            fa
            fa-expand
        [web.Element/title]
            {Locale/text}
                Full composer
        [web.Element/type]
            button
        [Element/onClick]
            {ComposerView/openFullComposer}
                @record
                .{ComposerViewComponent/composerView}
`;
