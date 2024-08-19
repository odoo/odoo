/** @odoo-module */

import { getColorPickerTemplateService } from '@html_editor/service/get_color_picker_template_service';
import { utils } from '@web/../tests/helpers/mock_env';
import { registry } from '@web/core/registry';
import { patch } from '@web/core/utils/patch';

const { prepareRegistriesWithCleanup } = utils;

const serviceRegistry = registry.category('services');
patch(utils, {
    prepareRegistriesWithCleanup() {
        prepareRegistriesWithCleanup(...arguments);
        serviceRegistry.add('get_color_picker_template', getColorPickerTemplateService);
    },
});
