/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('public_user_editor', {
    steps: () => [{
    trigger: '.note-editable',
}]});
