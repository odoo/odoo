import { patch } from '@web/core/utils/patch';

import { WebClient } from '@web/webclient/webclient';
import { AppsBar } from '@muk_web_appsbar/webclient/appsbar/appsbar';

/** Register the AppsBar so the web client renders the sidebar. */
patch(WebClient, {
    components: {
        ...WebClient.components,
        AppsBar,
    },
});
