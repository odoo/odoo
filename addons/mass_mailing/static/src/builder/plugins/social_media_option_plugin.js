import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { SocialMediaOptionPlugin } from "@website/builder/plugins/options/social_media_option_plugin";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { BuilderAction } from "@html_builder/core/builder_action";

export class SocialMediaOption extends BaseOptionComponent {
    static template = "mass_mailing.SocialMediaOption";
    /** @override */
    setup() {
        super.setup();
        this.companies = user.allowedCompanies;
    }
}

export class SelectCompanyAction extends BuilderAction {
    static id = "selectCompany";
    static dependencies = ["socialMediaOptionPlugin"];
    apply({ editingElement, value }) {
        this.dispatchTo("on_company_selected", editingElement, value);
    }
    /** @returns {boolean} */
    isApplied({ editingElement, params: value }) {
        return true;
    }
}

class MassMailingSocialMediaOptionPlugin extends SocialMediaOptionPlugin {
    resources = {
        ...this.resources,
        builder_actions: {
            ...this.resources.builder_actions,
            SelectCompanyAction,
        },
        patch_builder_options: [{
            target_name: "social_media_option",
            target_element: "OptionComponent",
            method: "replace",
            value: SocialMediaOption,
        }],
        /**
         * @param {HTMLElement} editingElement
         * @param {integer} companyId
         **/
        on_company_selected: async (editingElement, companyId) => {
            const medias = await this.fetchSocialMediaForCompany(companyId);
            this.updateBuilderOptions(medias);
            this.updateSnippet(editingElement, medias);
        },
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    async onSnippetDropped({ snippetEl }) {
        const medias = await this.fetchSocialMediaForCompany(user.activeCompany.id);
        this.updateBuilderOptions(medias);
        this.updateSnippet(snippetEl, medias);
    }

    /** @returns {Array[string]} */
    get plateforms () {
        return [
            "twitter",
            "facebook",
            "github",
            "linkedin",
            "youtube",
            "instagram",
            "tiktok",
            "discord"
        ];
    }

    /** @param {integer} companyId */
    async fetchSocialMediaForCompany(companyId) {
        const records = await this.services.orm.read(
            "res.company",
            [companyId],
            this.plateforms.map(plateform => `social_${plateform}`));
        // Remove the `social_` prefix:
        const medias = {};
        for (const [fieldName, href] of Object.entries(records[0])) {
            const matches = fieldName.match(/social_(\w+)/);
            const plateform = matches ? matches[1] : fieldName;
            medias[plateform] = href;
        }
        return medias;
    }

    /** @override */
    async saveRecordedSocialMedia() {
        return;
    }

    /**
     * @override
     * @param {Object} medias
     */
    updateBuilderOptions(medias) {
        for (const plateform of this.plateforms) {
            if (medias[plateform]) {
                const href = medias[plateform];
                this.recordedSocialMedia.set(plateform, href);
            }
        }
        this.config.onChange({ isPreviewing: false });
    }

    /**
     * @override
     * @param {HtmlElement} editingElement
     * @param {Object} medias
     */
    updateSnippet(editingElement, medias) {
        for (const [plateform, href] of Object.entries(medias)) {
            const link = editingElement.querySelector(`.s_social_media_${plateform}`);
            if (link) {
                link.href = href;
            }
        }
    }
}

registry.category("mass_mailing-plugins").add(MassMailingSocialMediaOptionPlugin.id, MassMailingSocialMediaOptionPlugin);
