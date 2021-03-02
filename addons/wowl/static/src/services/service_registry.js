/** @odoo-module **/

import { actionService } from "../actions/action_service";
import { Registry } from "../core/registry";
import { crashManagerService } from "../crash_manager/crash_manager_service";
import { notificationService } from "../notifications/notification_service";
import { cookieService } from "./cookie";
import { deviceService } from "./device";
import { dialogManagerService } from "./dialog_manager";
import { menusService } from "./menus";
import { modelService } from "./model";
import { routerService } from "./router";
import { rpcService } from "./rpc";
import { titleService } from "./title";
import { uiService } from "./ui/ui";
import { userService } from "./user";
import { viewService } from "../views/view_service";
import { debugManagerService } from "../debug_manager/debug_manager_service";
import { downloadService } from "./download";
import { effectService } from "../effects/effects_service";
import { localizationService } from "./localization";
import { currencyService } from "./currency";

export const serviceRegistry = new Registry();

const services = [
  actionService,
  crashManagerService,
  cookieService,
  currencyService,
  dialogManagerService,
  titleService,
  menusService,
  modelService,
  notificationService,
  routerService,
  rpcService,
  uiService,
  userService,
  viewService,
  debugManagerService,
  downloadService,
  effectService,
  deviceService,
  localizationService,
];
for (let service of services) {
  serviceRegistry.add(service.name, service);
}
