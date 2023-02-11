/**
 * This module exists so that web_tour can use it as the parent of the
 * TourManager so it can get access to _trigger_up.
 */
odoo.define("root.widget", function (require) {
    const { ComponentAdapter } = require("web.OwlCompatibility");
    const { Component } = owl;
    return new ComponentAdapter(null, { Component });
});
