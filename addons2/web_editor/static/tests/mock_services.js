/** @odoo-module */

import { patch } from '@web/core/utils/patch';
import { registry } from '@web/core/registry';
import { utils } from '@web/../tests/helpers/mock_env';
import { getColorPickerTemplateService } from '@web_editor/js/wysiwyg/get_color_picker_template_service';

const { prepareRegistriesWithCleanup } = utils;

const serviceRegistry = registry.category('services');
patch(utils, {
    prepareRegistriesWithCleanup() {
        prepareRegistriesWithCleanup(...arguments);
        serviceRegistry.add('get_color_picker_template', getColorPickerTemplateService);
    },
});
