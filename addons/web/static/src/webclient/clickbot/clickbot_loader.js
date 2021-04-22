/** @odoo-module alias=web.clickEverywhere **/

const { loadJS } = owl.utils;

export default async function startClickEverywhere(xmlId, appsMenusOnly) {
  await loadJS("web/static/src/webclient/clickbot/clickbot.js");
  window.clickEverywhere(xmlId, appsMenusOnly);
}
