/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The MediaStream from the camera.

        Default set to null to be consistent with the default value of
        'HTMLMediaElement.srcObject'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            videoStream
        [Field/model]
            MediaPreview
        [Field/type]
            attr
        [Field/target]
            MediaStream
`;
