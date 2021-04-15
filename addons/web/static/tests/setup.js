/** @odoo-module **/

import { legacyProm } from "web.test_legacy";
import { registerCleanup } from "./helpers/cleanup";
import { makeTestOdoo } from "./helpers/mock_env";
import { patchWithCleanup } from "./helpers/utils";

const { whenReady, loadFile } = owl.utils;

owl.config.enableTransitions = false;
owl.QWeb.dev = true;

export async function setupTests() {
  const originalOdoo = odoo;
  const listeners = new Map();
  const objectsToPatch = [window, document];

  QUnit.testStart(() => {
    odoo = makeTestOdoo();
    const originalLocale = luxon.Settings.defaultLocale;
    luxon.Settings.defaultLocale = "en";

    // Here we keep track of listeners added on the window and document objects.
    // Some stuff with permanent state (e.g. services) may register
    // those kind of listeners without removing them at some point.
    // We manually remove them after each test (see below).
    for (const obj of objectsToPatch) {
      listeners.set(obj, []);
    }
    for (const [obj, store] of listeners.entries()) {
      patchWithCleanup(obj, {
        addEventListener: function () {
          store.push([...arguments]);
          this._super(...arguments);
        },
      });
    }
    registerCleanup(() => {
      odoo = originalOdoo;
      luxon.Settings.defaultLocale = originalLocale;
      // Cleanup the listeners added on window in the current test.
      for (const [obj, store] of listeners.entries()) {
        for (const args of store) {
          obj.removeEventListener(...args);
        }
      }
    });
  });

  const templatesUrl = `/web/webclient/qweb/${new Date().getTime()}`;
  let templates = await loadFile(templatesUrl);
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
  templates = `<templates> ${owlTemplates.join("\n")} </templates>`;
  window.__ODOO_TEMPLATES__ = templates;
  await Promise.all([whenReady(), legacyProm]);
}
