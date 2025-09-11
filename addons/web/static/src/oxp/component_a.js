/** @odoo-module **/

import { Component, xml } from "@odoo/owl";
import { TodoInput } from "./todo_input";

export class ComponentA extends Component {
    static template = xml`<div><TodoInput/></div>`;
    static components = { TodoInput };
}
