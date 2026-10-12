import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields, models } from "@web/../tests/web_test_helpers";
import { unmockedOrm } from "@web/../tests/_framework/module_set.hoot";

const publicAssetsCache = new Map();

export class IrUiView extends models.Model {
    async render_public_asset(template, values) {
        const args = ["ir.ui.view", "render_public_asset", [template, values], {}];
        if (
            ["mass_mailing.email_designer_snippets", "mass_mailing.email_designer_themes"].includes(
                template
            )
        ) {
            if (!publicAssetsCache.has(template)) {
                publicAssetsCache.set(template, unmockedOrm(...args));
            }
            return publicAssetsCache.get(template);
        }
        return unmockedOrm(...args);
    }

    savedSnippetNum = 1000;

    async save_snippet() {
        const kwargs = arguments[0];
        // insert the snippet in publicAssetsCache
        let cacheValue = await publicAssetsCache.get("mass_mailing.email_designer_snippets");

        const findThis = 'snippets id="snippet_custom" string="Custom">';
        const insertIndex = cacheValue.indexOf(findThis) + findThis.length;
        cacheValue =
            cacheValue.slice(0, insertIndex) +
            `
            <div name="${kwargs.name}" data-oe-snippet-id="${this.savedSnippetNum}" 
                data-oe-thumbnail="${kwargs.thumbnail_url}" 
                data-oe-snippet-key="${kwargs.snippet_key + "_" + this.savedSnippetNum}" 
                data-oe-type="snippet" data-o-image-preview="">
                    ${kwargs.arch}
            </div>
            ` +
            cacheValue.slice(insertIndex);
        publicAssetsCache.set("mass_mailing.email_designer_snippets", cacheValue);
        this.savedSnippetNum += 1;
        return true;
    }
}

export class ResCompany extends models.Model {
    _name = "res.company";

    description = fields.Text();

    _records = mailModels.ResCompany._records;

    get_mailing_snippet_info() {
        return {
            has_logo: false,
            website: "https://www.odoo.com",
            email: "admin@example.com",
            contact_address: "Rue des Ursulines, 1000 Bruxelles",
            display_address: "Rue des Ursulines, 1000 Bruxelles",
            social_links: {
                social_facebook: "https://example.com/testLinkFacebook",
                social_twitter: "https://example.com/testLinkTwitter",
            },
        };
    }
}
