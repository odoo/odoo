import { Component } from "@odoo/owl";
import { ProjectList } from "@t9n/core/project_list";

/**
 * The "root", the "homepage" of the translation application.
 */
export class App extends Component {
    static components = { ProjectList };
    static props = {};
    static template = "t9n.App";
}
