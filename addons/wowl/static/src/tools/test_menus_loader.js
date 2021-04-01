/** @odoo-module alias=web.clickEverywhere **/

const { loadJS } = owl.utils;

export async function startClickEverywhere(xmlId, appsMenusOnly) {
  await loadJS("wowl/static/src/js/tools/test_menus.js");
  window.clickEverywhere(xmlId, appsMenusOnly);
}
