import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { SPECIAL_CARD_SELECTOR, CARD_PARENT_HANDLERS } from "./utils";

export class ClickableBlockOption extends BaseOptionComponent {
    static template = "website.ClickableBlockOption";
    static selector = `.s_card`;
    static exclude = `${SPECIAL_CARD_SELECTOR}`;

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            hasHref: editingElement.querySelector("a.stretched-link")?.hasAttribute("href"),
        }));
    }
}

export class ClickableCardParentOption extends ClickableBlockOption {
    static selector = CARD_PARENT_HANDLERS;
    static exclude = ".s_carousel_cards_item";
    static applyTo = ".s_card";
}
