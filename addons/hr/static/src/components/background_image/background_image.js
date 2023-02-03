/** @odoo-module */

import { registry } from '@web/core/registry';

import { ImageField, imageField } from '@web/views/fields/image/image_field';

export class BackgroundImageField extends ImageField {}
BackgroundImageField.template = 'hr.BackgroundImage';

export const backgroundImageField = {
    ...imageField,
    component: BackgroundImageField,
};

registry.category("fields").add("background_image", backgroundImageField);
