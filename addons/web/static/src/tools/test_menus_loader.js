/** @odoo-module alias=web.clickEverywhere **/

const { loadJS } = owl.utils;

export async function startClickEverywhere(xmlId, appsMenusOnly) {
  await loadJS("web/static/src/wowl/tools/test_menus.js");
  window.clickEverywhere(xmlId, appsMenusOnly);
}
