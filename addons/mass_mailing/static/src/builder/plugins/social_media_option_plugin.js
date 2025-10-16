import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { SNIPPET_SPECIFIC, TITLE_LAYOUT_SIZE } from "@html_builder/utils/option_sequence";
import { SocialMediaLinks } from "../options/social_media_links";
import { SocialMediaOptions } from "../options/social_media_option";
import { renderToElement } from "@web/core/utils/render";

class MassMailingSocialMediaOptionPlugin extends Plugin {
    static id = "massMailingSocialMediaOptionPlugin";
    resources = {
        builder_options: [
            withSequence(TITLE_LAYOUT_SIZE, {
                name: "social_media_option",
                selector: ".s_share, .s_social_media",
                OptionComponent: SocialMediaOptions,
            }),
            withSequence(SNIPPET_SPECIFIC, {
                name: "social_media_links",
                selector: ".s_social_media",
                OptionComponent: SocialMediaLinks,
                props: {
                    fetchRecordedSocialMedia: this.fetchRecordedSocialMedia.bind(this)
                },
            }),
        ],
        so_content_addition_selector: [".s_share", ".s_social_media"],
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    /** @override */
    async onSnippetDropped({ snippetEl }) {
        const companyId = user.activeCompany.id;
        const medias = await this.fetchRecordedSocialMedia(companyId);
        for (const [plateform, href] of Object.entries(medias)) {
            const element = renderToElement("mass_mailing.social_media_link", {
                href: href || "",
                plateform,
                icon: `fa-${plateform}`,
            });
            snippetEl.append(element);
        }
        snippetEl.setAttribute("data-company-id", companyId);
    }

    /** @returns {Array[string]} */
    get plateforms() {
        return [
            "twitter",
            "facebook",
            "github",
            "linkedin",
            "youtube",
            "instagram",
            "tiktok",
            "discord",
        ];
    }

    /** @param {integer} companyId */
    async fetchRecordedSocialMedia(companyId) {
        const records = await this.services.orm.read(
            "res.company",
            [companyId],
            this.plateforms.map((plateform) => `social_${plateform}`)
        );
        // Remove the `social_` prefix from the fields:
        const medias = {};
        for (const [fieldName, href] of Object.entries(records[0])) {
            const matches = fieldName.match(/social_(\w+)/);
            if (matches) {
                const plateform = matches[1];
                if (this.plateforms.includes(plateform)) {
                    medias[plateform] = href;
                }
            }
        }
        return medias;
    }
}

registry
    .category("mass_mailing-plugins")
    .add(MassMailingSocialMediaOptionPlugin.id, MassMailingSocialMediaOptionPlugin);
