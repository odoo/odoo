/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonEmojis
        [Element/model]
            ComposerViewComponent
        [web.Element/tag]
            button
        [Record/models]
            ComposerViewComponent/button
            ComposerViewComponent/toolButton
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-light
        [Element/onClick]
            {ComposerView/onClickButtonEmojis}
                [0]
                    @record
                    .{ComposerViewComponent/composerView}
                [1]
                    @ev
        [Element/onKeydown]
            {ComposerView/onKeydownButtonEmojis}
                [0]
                    @record
                    .{ComposerViewComponent/composerView}
                [1]
                    @ev
`;
