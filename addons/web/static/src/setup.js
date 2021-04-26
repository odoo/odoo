/** @odoo-module **/

import { makeEnv } from "./env";
import { mapLegacyEnvToWowlEnv } from "./legacy/utils";
import { legacySetupProm } from "./legacy/legacy_setup";

const { mount, utils } = owl;
const { whenReady } = utils;

export async function startWebClient(webclient) {
  // delete (odoo as any).session_info; // FIXME: some legacy code rely on this (e.g. ajax.js)
  const sessionInfo = odoo.session_info;
  odoo.info = {
    db: sessionInfo.db,
    server_version: sessionInfo.server_version,
    server_version_info: sessionInfo.server_version_info,
  };

  // setup environment
  const loadTemplates = odoo.loadTemplatesPromise.then(processTemplates);
  const [env, templates] = await Promise.all([makeEnv(odoo.debug), loadTemplates]);
  env.qweb.addTemplates(templates);

  // start web client
  await whenReady();
  const legacyEnv = await legacySetupProm;
  mapLegacyEnvToWowlEnv(legacyEnv, env);
  const root = await mount(webclient, { env, target: document.body, position: "self" });
  delete odoo.debug;
  odoo.__WOWL_DEBUG__ = { root };
}

/**
 * Process the qweb templates to obtain only the owl templates. This method
 * does NOT register the templates into Owl.
 *
 * @param {String} templates
 * @returns {String} returns a strings containing only owl templates
 */
 export function processTemplates(templates) {
  // as we currently have two qweb engines (owl and legacy), owl templates are
  // flagged with attribute `owl="1"`. The following lines removes the 'owl'
  // attribute from the templates, so that it doesn't appear in the DOM. For now,
  // we make the assumption that 'templates' only contains owl templates. We
  // might need at some point to handle the case where we have both owl and
  // legacy templates. At the end, we'll get rid of all this.
  const doc = new DOMParser().parseFromString(templates, "text/xml");
  const owlTemplates = [];
  for (let child of doc.querySelectorAll("templates > [owl]")) {
      child.removeAttribute("owl");
      owlTemplates.push(child.outerHTML);
  }
  return `<templates> ${owlTemplates.join("\n")} </templates>`;
}
