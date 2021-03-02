/** @odoo-module alias=wowl.legacySetup **/

import { serviceRegistry } from "../webclient/service_registry";
import {
  makeLegacyActionManagerService,
  makeLegacyRpcService,
  makeLegacySessionService,
} from "./utils";
import * as AbstractService from "web.AbstractService";
import * as legacyEnv from "web.env";
import * as session from "web.session";
import * as makeLegacyWebClientService from "wowl.pseudo_web_client";

const { Component, config, utils } = owl;
const { whenReady } = utils;

let legacySetupResolver;
export const legacySetupProm = new Promise((resolve) => {
  legacySetupResolver = resolve;
});

// build the legacy env and set it on owl.Component (this was done in main.js,
// with the starting of the webclient)
(async () => {
  config.mode = legacyEnv.isDebug() ? "dev" : "prod";
  AbstractService.prototype.deployServices(legacyEnv);
  Component.env = legacyEnv;
  const legacyActionManagerService = makeLegacyActionManagerService(legacyEnv);
  serviceRegistry.add(legacyActionManagerService.name, legacyActionManagerService);
  // add a service to redirect rpc events triggered on the bus in the
  // legacy env on the bus in the wowl env
  const legacyRpcService = makeLegacyRpcService(legacyEnv);
  serviceRegistry.add(legacyRpcService.name, legacyRpcService);
  const legacySessionService = makeLegacySessionService(legacyEnv, session);
  serviceRegistry.add(legacySessionService.name, legacySessionService);
  const legacyWebClientService = makeLegacyWebClientService(legacyEnv);
  serviceRegistry.add(legacyWebClientService.name, legacyWebClientService);
  await Promise.all([whenReady(), session.is_bound]);
  legacyEnv.qweb.addTemplates(session.owlTemplates);
  legacySetupResolver(legacyEnv);
})();
