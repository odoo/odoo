/** @odoo-module **/

import { registry } from '@web/core/registry';

const viewArchsRegistry = registry.category('bus.view.archs');
const calendarArchsRegistry = viewArchsRegistry.category('calendar');

calendarArchsRegistry.add('default', '<calendar date_start="start"/>');
