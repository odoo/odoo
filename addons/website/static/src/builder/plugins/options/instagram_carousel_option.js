import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

export class InstagramCarouselOption extends BaseOptionComponent {
    static id = "instagram_carousel_option";
    static template = "website.InstagramCarouselOption";
    static dependencies = ["dynamicSnippetOption"];

    setup() {
        super.setup();
        this.getSnippetTitleClasses = this.dependencies.dynamicSnippetOption.getSnippetTitleClasses;
        onWillStart(async () => {
            this.canConnect = await user.hasGroup("website.group_website_designer");
        });
        this.domState = useDomState((editingElement) => ({
            numberOfRecords: parseInt(editingElement.dataset.numberOfRecords),
        }));
    }
}

registry.category("website-options").add(InstagramCarouselOption.id, InstagramCarouselOption);
