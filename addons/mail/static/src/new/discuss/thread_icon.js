/** @odoo-module */

import { Component } from "@odoo/owl";

export class ThreadIcon extends Component {}

Object.assign(ThreadIcon, {
    props: ["thread", "className?"],
    template: "mail.thread_icon",
});
