/** @odoo-module **/
import { startWebClient } from '@web/start';
import { ProjectSharingWebClient } from './project_sharing';
import { prepareFavoriteMenuRegister } from './components/favorite_menu_registry';

prepareFavoriteMenuRegister();
startWebClient(ProjectSharingWebClient);
