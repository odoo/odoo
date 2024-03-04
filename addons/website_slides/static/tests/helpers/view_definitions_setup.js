/** @odoo-module **/

import { registry } from '@web/core/registry';

const viewArchsRegistry = registry.category('bus.view.archs');

viewArchsRegistry.category('form').add(
    'slide.channel',
    `<form>
        <chatter/>
    </form>`
);
