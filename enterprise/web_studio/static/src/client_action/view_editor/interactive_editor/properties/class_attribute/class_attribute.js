import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Property } from "@web_studio/client_action/view_editor/property/property";

export class ClassAttribute extends Component {
    static template = "web_studio.ViewEditor.ClassAttribute";
    static components = {
        Property,
    };
    static props = {
        value: { type: String, optional: true },
        onChange: { type: Function },
    };
    get tooltip() {
        return _t(
            "Use Bootstrap or any other custom classes to customize the style and the display of the element."
        );
    }
}
