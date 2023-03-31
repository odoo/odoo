/** @odoo-module alias=root.widget **/
/**
 * This module exists so that web_tour can use it as the parent of the
 * TourManager so it can get access to _trigger_up.
 */
// need to wait for owl.Component.env to be set by new/public/boot before
// we spawn the component adapter
import "@mail/public/boot";
import { standaloneAdapter } from "web.OwlCompatibility";
import { Component } from "@odoo/owl";

export default standaloneAdapter({ Component });
