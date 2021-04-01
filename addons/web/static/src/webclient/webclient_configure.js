/** @odoo-module alias=web.WebClientConfigure **/
// keep this alias, it is needed to override the configuration for booting the webclient

// AAB FIXME: this module is no longer necessary. If we want to keep this logic, we
// can directly have a web.WebClient module alias in community, overriden in
// enterprise
import { WebClient } from "./webclient";

// LPE FIXME: this is only because the module is aliased
export default function configure() {
  return WebClient;
}
