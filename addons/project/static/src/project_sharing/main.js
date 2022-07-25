/** @odoo-module **/

import { startWebClient } from '@web/start';
import { ProjectSharingWebClient } from './project_sharing';
import { prepareFavoriteMenuRegister } from './components/favorite_menu_registry';
import { prepareMessaging } from './utils';

prepareFavoriteMenuRegister();
prepareMessaging();
startWebClient(ProjectSharingWebClient);
