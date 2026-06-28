import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { props, t } from "@odoo/owl";

export class ShadowOption extends BaseOptionComponent {
    static template = "html_builder.ShadowOption";
    props = props({
        setShadowClassAction: t.string().optional("setShadowClass"),
        setShadowModeAction: t.string().optional("setShadowMode"),
        setShadowStyleAction: t.string().optional("setShadowStyle"),
    });

    getOnClick(shadowClass) {
        return () => this.env.editShadow(shadowClass);
    }
}
