import { BaseOptionComponent } from "@html_builder/core/utils";
import { basicHeaderOptionSettings } from "./basicHeaderOptionSettings";

export class HeaderFontOption extends BaseOptionComponent {
    static template = "website.HeaderFontOption";
}

Object.assign(HeaderFontOption, basicHeaderOptionSettings);
