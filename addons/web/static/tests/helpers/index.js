/** @odoo-module **/

import { setTemplates } from "./utility";
import { legacyProm } from "web.test_legacy";
import { makeTestOdoo } from "./mocks";
import { registerCleanup } from "./cleanup";
import { patch, unpatch } from "../../src/utils/patch";

const { whenReady, loadFile } = owl.utils;

let templates;

owl.config.enableTransitions = false;
owl.QWeb.dev = true;

export async function setupTests() {
  const originalOdoo = odoo;
  const listeners = new Map();
  const objectsToPatch = [window, document];
  const listenerPatchName = "wowl/tests/helpers/custom listeners";

  QUnit.testStart(() => {
    odoo = makeTestOdoo();

    // Here we keep track of listeners added on the window and document objects.
    // Some stuff with permanent state (e.g. services) may register
    // those kind of listeners without removing them at some point.
    // We manually remove them after each test (see below).
    for (const obj of objectsToPatch) {
      listeners.set(obj, []);
    }
    for (const [obj, store] of listeners.entries()) {
      patch(obj, listenerPatchName, {
        addEventListener: function () {
          store.push([...arguments]);
          this._super(...arguments);
        },
      });
    }
    registerCleanup(() => {
      odoo = originalOdoo;

      // Cleanup the listeners added on window in the current test.
      for (const [obj, store] of listeners.entries()) {
        for (const args of store) {
          obj.removeEventListener(...args);
        }
        unpatch(obj, listenerPatchName);
      }
    });
  });

  const templatesUrl = `/web/webclient/qweb/${new Date().getTime()}`;
  templates = await loadFile(templatesUrl);
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
  setTemplates(templates);
  await Promise.all([whenReady(), legacyProm]);
}

export { makeFakeUserService, makeFakeRPCService, makeMockXHR, makeMockFetch } from "./mocks";

export {
  click,
  getFixture,
  makeTestServiceRegistry,
  makeTestViewRegistry,
  makeDeferred,
  makeTestEnv,
  nextTick,
  patchDate,
  triggerEvent,
} from "./utility";
