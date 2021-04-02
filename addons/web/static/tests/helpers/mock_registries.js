/** @odoo-module **/

import { actionService } from "../../src/actions/action_service";
import { Registry } from "../../src/core/registry";
import { effectService } from "../../src/effects/effect_service";
import { hotkeyService } from "../../src/hotkey/hotkey_service";
import { notificationService } from "../../src/notifications/notification_service";
import { dialogService } from "../../src/services/dialog_service";
import { menuService } from "../../src/services/menu_service";
import { ormService } from "../../src/services/orm_service";
import { popoverService } from "../../src/services/popover_service";
import { uiService } from "../../src/services/ui_service";
import { viewRegistry } from "../../src/views/view_registry";
import { viewService } from "../../src/views/view_service";
import {
  fakeTitleService,
  makeFakeRouterService,
  makeFakeUserService
} from "./mock_services";


export function makeTestServiceRegistry() {
  // build the service registry

  // need activateMockServer or something like that for odoo.browser.fetch !!! something is bad
  const testServiceRegistry = new Registry();
  const fakeUserService = makeFakeUserService();
  const fakeRouterService = makeFakeRouterService();

  testServiceRegistry
    .add("user", fakeUserService)
    .add("notification", notificationService)
    .add("dialog", dialogService)
    .add("menu", menuService)
    .add("action", actionService)
    .add("router", fakeRouterService)
    .add("view", viewService)
    .add("orm", ormService)
    .add("title", fakeTitleService)
    .add("ui", uiService)
    .add("effect", effectService)
    .add("hotkey", hotkeyService)
    .add("popover", popoverService);
  return testServiceRegistry;
}

export function makeTestViewRegistry() {
  // build a copy of the view registry
  const testViewRegistry = new Registry();
  for (const [key, view] of viewRegistry.getEntries()) {
    testViewRegistry.add(key, view);
  }
  return testViewRegistry;
}
