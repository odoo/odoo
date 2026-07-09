import { Component, onWillStart, props, proxy, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export const FIELD_NAMES = [
    {
        displayName: _t("X Account"),
        iconClass: "oi_twitter",
        name: "social_twitter",
        placeholder: "https://twitter.com/Odoo",
    },
    {
        displayName: _t("Facebook Account"),
        iconClass: "oi_facebook",
        name: "social_facebook",
        placeholder: "https://www.facebook.com/Odoo",
    },
    {
        displayName: _t("Github Account"),
        iconClass: "oi_github",
        name: "social_github",
        placeholder: "https://github.com/odoo",
    },
    {
        displayName: _t("Linkedin Account"),
        iconClass: "oi_linkedin",
        name: "social_linkedin",
        placeholder: "https://www.linkedin.com/company/odoo",
    },
    {
        displayName: _t("Youtube Account"),
        iconClass: "oi_youtube",
        name: "social_youtube",
        placeholder: "https://www.youtube.com/user/OpenERPonline",
    },
    {
        displayName: _t("Instagram Account"),
        iconClass: "oi_instagram",
        name: "social_instagram",
        placeholder: "https://www.instagram.com/explore/tags/odoo/",
    },
    {
        displayName: _t("Tiktok Account"),
        iconClass: "oi_tiktok",
        name: "social_tiktok",
        placeholder: "https://www.tiktok.com/@odoo",
    },
    {
        displayName: _t("Discord Account"),
        iconClass: "oi_discord",
        name: "social_discord",
        placeholder: "https://discord.com/servers/discord-town-hall-169256939211980800",
    },
];

export class ResCompanyUpdateDialog extends Component {
    static template = "mass_mailing.CompanyUpdateDialog";
    static components = { Dialog };
    props = props({
        close: t.function(),
        onRecordSaved: t.function().optional(() => () => {}),
        onCancel: t.function().optional(() => () => {}),
        resId: t.number(),
    });

    setup() {
        this.orm = useService("orm");
        this.state = proxy({});
        onWillStart(async () => {
            const [record] = await this.orm.read(
                "res.company",
                [this.props.resId],
                ["display_name", ...FIELD_NAMES.map((field) => field.name)]
            );
            this.displayName = record.display_name;
            FIELD_NAMES.forEach(({ name }) => (this.state[name] = record[name] || ""));
        });
        this.fieldNames = FIELD_NAMES;
    }

    get dialogTitle() {
        return _t("Configure your Social Media Links for %s", this.displayName);
    }

    async clickOnSave() {
        await this.orm.call("res.company", "update_social_links", [this.props.resId], {
            social_links: this.state,
        });
        this.props.onRecordSaved({ ...this.state });
        this.props.close();
    }
    cancel() {
        this.props.onCancel();
        this.props.close();
    }
}
