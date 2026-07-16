import { registry } from "@web/core/registry";
import { Component, xml } from "@odoo/owl";
import { Widget } from "@web/views/widgets/widget";
import { Field } from "@web/views/fields/field";

/**
 * Backend views opened from within the PoS UI (order details dialog,
 * drill-down on many2one links, ...) share their arch with the backend, so
 * they can reference widgets whose implementation is only bundled in
 * `web.assets_backend` (e.g. `pos_payment_provider_cards`, `lna_checklist`,
 * `many2many_tax_tags`). Unlike missing field widgets, an unknown view widget
 * makes the whole view crash. Those widgets are backend helpers that are
 * irrelevant in a PoS session, so skip them instead. Logging stays below
 * warning level: missing backend widgets are expected in the PoS bundle.
 */
class UnavailableWidget extends Component {
    static template = xml`<t/>`;
    static props = ["*"];
}

const viewWidgetRegistry = registry.category("view_widgets");
const superParseWidgetNode = Widget.parseWidgetNode;
Widget.parseWidgetNode = function (node) {
    const name = node.getAttribute("name");
    if (!viewWidgetRegistry.contains(name)) {
        console.info(`Missing widget: ${name}`);
        return { name, widget: { component: UnavailableWidget }, options: {}, attrs: {} };
    }
    return superParseWidgetNode.call(this, node);
};

const fieldRegistry = registry.category("fields");
const superParseFieldNode = Field.parseFieldNode;
Field.parseFieldNode = function (node, models, modelName, viewType, jsClass) {
    const widget = node.getAttribute("widget");
    if (widget) {
        const prefixes = jsClass ? [jsClass, viewType, ""] : [viewType, ""];
        if (!prefixes.some((p) => fieldRegistry.contains(p ? `${p}.${widget}` : widget))) {
            console.info(`Missing widget: ${widget}`);
            node.removeAttribute("widget");
        }
    }
    return superParseFieldNode.call(this, node, models, modelName, viewType, jsClass);
};
