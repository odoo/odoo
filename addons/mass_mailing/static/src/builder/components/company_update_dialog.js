import { Component, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export const FIELD_NAMES = [
    {
        displayName: _t("X Account"),
        name: "social_twitter",
        placeholder: "https://twitter.com/Odoo",
    },
    {
        displayName: _t("Facebook Account"),
        name: "social_facebook",
        placeholder: "https://www.facebook.com/Odoo",
    },
    {
        displayName: _t("Github Account"),
        name: "social_github",
        placeholder: "https://github.com/odoo",
    },
    {
        displayName: _t("Linkedin Account"),
        name: "social_linkedin",
        placeholder: "https://www.linkedin.com/company/odoo",
    },
    {
        displayName: _t("Youtube Account"),
        name: "social_youtube",
        placeholder: "https://www.youtube.com/user/OpenERPonline",
    },
    {
        displayName: _t("Instagram Account"),
        name: "social_instagram",
        placeholder: "https://www.instagram.com/explore/tags/odoo/",
    },
    {
        displayName: _t("Tiktok Account"),
        name: "social_tiktok",
        placeholder: "https://www.tiktok.com/@odoo",
    },
    {
        displayName: _t("Discord Account"),
        name: "social_discord",
        placeholder: "https://discord.com/servers/discord-town-hall-169256939211980800",
    },
];

export class ResCompanyUpdateDialog extends Component {
    static template = "mass_mailing.CompanyUpdateDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        onRecordSaved: { type: Function, optional: true },
        onCancel: { type: Function, optional: true },
        resId: Number,
    };
    static defaultProps = {
        onRecordSaved: () => {},
        onCancel: () => {},
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({});
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
