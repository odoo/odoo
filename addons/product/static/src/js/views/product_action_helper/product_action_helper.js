import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, t, useProps } from "@odoo/owl";

export const productCreateHelperButtons = registry.category("product_create_helper_buttons");

productCreateHelperButtons.add("goods", {
    sequence: 10,
    label: _t("Goods"),
    description: _t("Physical products you can stock and sell"),
    icon: "package_2",
    context: { default_type: "consu" },
});
productCreateHelperButtons.add("services", {
    sequence: 20,
    label: _t("Services"),
    description: _t("Time or expertise provided to client, like consulting, installation, support."),
    icon: "headphones",
    context: { default_type: "service" },
});
productCreateHelperButtons.add("combo", {
    sequence: 30,
    label: _t("Combo"),
    description: _t("A group of products sold together as a single offering"),
    icon: "widgets",
    context: { default_type: "combo" },
});

export const productImportHelperLinks = registry.category("product_import_helper_links");

productImportHelperLinks.add("import_file", {
    sequence: 10,
    label: _t("Import File"),
    icon: "upload",
    run: ({ action }) => {
        action.doAction({
            type: "ir.actions.client",
            tag: "import",
            params: { active_model: "product.template" },
        });
    },
});

export class ProductActionHelper extends Component {
    static template = "product.ProductActionHelper";

    props = useProps({
        noContentHelp: t.string().optional(),
    });

    setup() {
        this.action = useService("action");
        this.dialog = useService("dialog");
    }

    getButtons() {
        return productCreateHelperButtons.getAll();
    }

    getImportLinks() {
        return productImportHelperLinks.getAll();
    }

    createProduct(entry) {
        this.action.doAction({
            res_model: "product.template",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            view_mode: "form",
            target: "current",
            context: entry.context,
        });
    }

    runImportLink(entry) {
        entry.run({ action: this.action, dialog: this.dialog });
    }
}
