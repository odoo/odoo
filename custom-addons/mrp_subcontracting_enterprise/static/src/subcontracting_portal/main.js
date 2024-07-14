/** @odoo-module  **/

import { startWebClient } from '@web/start';
import { SubcontractingPortalWebClient } from '@mrp_subcontracting/subcontracting_portal/subcontracting_portal';
import { removeServices } from './remove_services';

removeServices();
startWebClient(SubcontractingPortalWebClient);
