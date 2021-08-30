/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonAttachment
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
            fa-paperclip
        [web.Element/title]
            {Locale/text}
                Add attachment
        [web.Element/type]
            button
        [Element/onClick]
            {ComposerViewComponent/_onClickAddAttachment}
                @record
                @ev
`;
