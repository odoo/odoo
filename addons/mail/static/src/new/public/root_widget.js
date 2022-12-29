/**
 * This module exists so that web_tour can use it as the parent of the
 * TourManager so it can get access to _trigger_up.
 */
odoo.define("root.widget", function (require) {
    // need to wait for owl.Component.env to be set by new/public/boot before
    // we spawn the component adapter
    require("@mail/new/public/boot");
    const { standaloneAdapter } = require("web.OwlCompatibility");
    const { Component } = require("@odoo/owl");
    return standaloneAdapter({ Component });
});
