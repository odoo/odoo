// @ts-check

/** @module @web/webclient/debug/profiling/profiling_systray_item - Systray indicator icon shown when Python profiling is active */

import { Component } from "@odoo/owl";

/** Systray indicator shown when profiling is active. */
class ProfilingSystrayItem extends Component {
    static template = "web.ProfilingSystrayItem";
    static props = {};
}

export const profilingSystrayItem = {
    Component: ProfilingSystrayItem,
};
