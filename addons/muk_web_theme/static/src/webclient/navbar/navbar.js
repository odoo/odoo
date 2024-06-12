/** @odoo-module */

import { patch } from '@web/core/utils/patch';
import { useService } from '@web/core/utils/hooks';

import { NavBar } from '@web/webclient/navbar/navbar';
import { AppsMenu } from "@muk_web_theme/webclient/appsmenu/appsmenu";

patch(NavBar.prototype, {
	setup() {
        super.setup();
        this.appMenuService = useService('app_menu');
    },
});

patch(NavBar, {
    components: {
        ...NavBar.components,
        AppsMenu,
    },
});
