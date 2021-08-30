/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Size class of the device.

        This is an integer representation of the size.
        Useful for conditional based on a device size, including
        lower/higher. Device size classes are defined in sizeClasses
        attribute.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            sizeClass
        [Field/model]
            Device
        [Field/type]
            attr
        [Field/target]
            Number
`;
