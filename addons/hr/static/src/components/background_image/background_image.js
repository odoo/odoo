/** @odoo-module */

import { registry } from '@web/core/registry';

import { ImageField } from '@web/views/fields/image/image_field';

export class BackgroundImageField extends ImageField {}
BackgroundImageField.template = 'hr.BackgroundImage';

registry.category("fields").add("background_image", BackgroundImageField);
