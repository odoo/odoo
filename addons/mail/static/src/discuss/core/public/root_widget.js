/* @odoo-module alias=root.widget */
/**
 * This module exists so that web_tour can use it as the parent of the
 * TourManager so it can get access to _trigger_up.
 */
// need to wait for owl.Component.env to be set by new/public/boot before
// we spawn the component adapter
import "@mail/discuss/core/public/boot";

import { Component } from "@odoo/owl";

import { standaloneAdapter } from "web.OwlCompatibility";

export default standaloneAdapter({ Component });
