import { ImageAndFaOption } from "@html_builder/plugins/image/image_and_fa_option";
import { socialMediaElementsSelector } from "@html_builder/plugins/image/replace_media_option";

export class WebsiteImageAndFaOption extends ImageAndFaOption {
    static exclude = `[data-oe-type='image'] > img, [data-oe-xpath], ${socialMediaElementsSelector}`;
}
