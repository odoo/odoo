/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component } = owl;
export class BadgeField extends Component {}
BadgeField.getClassFromDecoration = (decoration) => `bg-${decoration}-light`;
BadgeField.template = "web.BadgeField";

registry.category("fields").add("badge", BadgeField);
