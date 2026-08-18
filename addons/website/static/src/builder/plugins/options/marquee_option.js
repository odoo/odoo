import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class MarqueeOption extends BaseOptionComponent {
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            // Compatibility before .o_marquee_pause button.
            hasPauseButton: !!editingElement.querySelector(".o_marquee_pause"),
        }));
    }
}

export class AnnouncementScrollOption extends MarqueeOption {
    static id = "announcement_scroll_option";
    static template = "website.AnnouncementScrollOption";
}

export class ReferencesCarouselOption extends MarqueeOption {
    static id = "references_carousel_option";
    static template = "website.ReferencesCarouselOption";
}

registry.category("website-options").add(AnnouncementScrollOption.id, AnnouncementScrollOption);
registry.category("website-options").add(ReferencesCarouselOption.id, ReferencesCarouselOption);
