/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles change of this composer. Useful to reset the state of the
        composer text input.
    {onChange}
        [onChange/name]
            _onChangeComposer
        [onChange/model]
            ComposerView
        [onChange/dependencies]
            ComposerView/composer
        [onChange/behavior]
            {Record/update}
                [0]
                    @record
                    .{ComposerView/composer}
                [1]
                    [Composer/isLastStateChangeProgrammatic]
                        true
`;