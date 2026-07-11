import { patch } from '@web/core/utils/patch';
import { useService } from '@web/core/utils/hooks';

import { NavBar } from '@web/webclient/navbar/navbar';
import { AppsMenu } from '@muk_web_theme/webclient/appsmenu/appsmenu';

/** Add the app-menu service to the navbar setup. */
patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.appMenuService = useService('app_menu');
    },
});

/** Register the themed AppsMenu as a navbar component. */
patch(NavBar, {
    components: {
        ...NavBar.components,
        AppsMenu,
    },
});
