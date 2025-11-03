import {
    BaseOptionComponent,
    useGetItemValue,
    BLOCKQUOTE_DISABLE_WIDTH_APPLY_TO,
    BLOCKQUOTE_PARENT_HANDLERS,
    SPECIAL_BLOCKQUOTE_SELECTOR,
} from "@html_builder/core/utils";
import { BaseWebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { ShadowOption } from "@html_builder/plugins/shadow_option";

export class BaseBlockquoteOption extends BaseOptionComponent {
    static template = "website.BlockquoteOption";
    static components = {
        BaseWebsiteBackgroundOption,
        BorderConfigurator,
        ShadowOption,
    };
    static props = {
        disableWidth: { type: Boolean, optional: true },
    };
    static defaultProps = {
        disableWidth: false,
    };
    setup() {
        super.setup();
        this.getItemValue = useGetItemValue();
    }
}

export class BlockquoteOption extends BaseBlockquoteOption {
    static selector = ".s_blockquote";
    static exclude = SPECIAL_BLOCKQUOTE_SELECTOR;
}

export class BlockquoteWithoutWidthOption extends BaseBlockquoteOption {
    static selector = BLOCKQUOTE_PARENT_HANDLERS;
    static applyTo = BLOCKQUOTE_DISABLE_WIDTH_APPLY_TO;
    static defaultProps = {
        disableWidth: true,
    };
}
