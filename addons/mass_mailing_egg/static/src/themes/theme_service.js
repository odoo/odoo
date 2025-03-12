import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { Reactive } from "@web/core/utils/reactive";

export class ThemeModel extends Reactive {
    constructor(services) {
        super();
        this.orm = services.orm;
        this.mutex = new Mutex();
        this.loadedAssets = new Map();
    }

    async load(themesPublicAsset = "mass_mailing.email_designer_themes") {
        if (!this.loadedAssets.has(themesPublicAsset)) {
            const themesHTML = await this.orm.silent.call(
                "ir.ui.view",
                "render_public_asset",
                [themesPublicAsset, {}],
                {}
            );
            const themesDocument = new DOMParser().parseFromString(themesHTML, "text/html");
            this.computeThemesTemplates(themesDocument);
            
        }
    }
}

registry.category("services").add("mass_mailing_egg.themes", {
    dependencies: ["orm"],

    start(env, { orm }) {
        const services = { orm };
        return new ThemeModel(services);
    },
});
