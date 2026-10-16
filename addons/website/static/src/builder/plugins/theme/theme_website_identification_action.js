import { BuilderAction } from "@html_builder/core/builder_action";
import { LOGO_TARGETS_NAME } from "./theme_website_identification_util";

export class BaseWebsiteBrandingAction extends BuilderAction {
    static dependencies = ["websiteBrandingPlugin"];
}

export class SetWebsiteNameAction extends BaseWebsiteBrandingAction {
    static id = "setWebsiteName";

    getValue() {
        return this.dependencies.websiteBrandingPlugin.getWebsiteName();
    }

    apply({ value }) {
        this.dependencies.websiteBrandingPlugin.updateName(value);
    }
}

export class BaseChangeMediaAction extends BaseWebsiteBrandingAction {
    canTimeout = false;
}

export class RemoveFaviconAction extends BaseWebsiteBrandingAction {
    static id = "removeFavicon";
    apply() {
        this.dependencies.websiteBrandingPlugin.removeFavicon();
    }
}

export class RestoreLogoAction extends BaseChangeMediaAction {
    static id = "restoreLogo";
    apply({ params }) {
        return this.dependencies.websiteBrandingPlugin.restoreLogo(params.mainParam);
    }
}

export class ReplaceFaviconAction extends BaseChangeMediaAction {
    static id = "replaceFavicon";
    apply() {
        return this.dependencies.websiteBrandingPlugin.updateFavicon();
    }
}

export class ReplaceLogoAction extends BaseChangeMediaAction {
    static id = "replaceLogo";
    apply({ params }) {
        return this.dependencies.websiteBrandingPlugin.updateLogo(
            params?.mainParam ? [params.mainParam] : LOGO_TARGETS_NAME
        );
    }
}
