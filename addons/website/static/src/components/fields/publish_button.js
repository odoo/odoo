/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component } = owl;

class PublishField extends Component {}
PublishField.template = "website.PublishField";

registry.category("fields").add("website_publish_button", PublishField);
