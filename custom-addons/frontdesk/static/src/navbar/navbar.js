/** @odoo-module **/

import { Component } from "@odoo/owl";

export class Navbar extends Component {}

Navbar.template = "frontdesk.Navbar";
Navbar.props = {
    companyInfo: Object,
    currentComponent: String,
    isMobile: Boolean,
    isPlannedVisitors: Boolean,
    showScreen: Function,
    onChangeLang: Function,
    theme: String,
    langs: [Object, Boolean],
    currentLang: String,
};
