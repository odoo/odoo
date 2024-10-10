import { Component, useState, xml } from "@odoo/owl";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class LinkPreviewSettings extends Component {
    static components = { ActionPanel, Dropdown, DropdownItem };
    static props = ["hasSizeConstraints?", "close?", "className?"];
    static template = "mail.linkPreviewSettings";

    setup() {
        this.store = useState(useService("mail.store"));
        this.dialog = useService("dialog");
    }

    onChangeLinkPreviewHtml(ev) {
        this.store.settings.setLinkPreviewHtml(!this.store.settings.link_preview_html);
    }

    onChangeLinkPreviewImage(ev) {
        this.store.settings.setLinkPreviewImage(!this.store.settings.link_preview_image);
    }
}

export class LinkPreviewSettingsClientAction extends Component {
    static components = { LinkPreviewSettings };
    static props = ["*"];
    static template = xml`
        <div class="o-mail-LinkPreviewSettingsClientAction mx-3 my-2">
            <LinkPreviewSettings/>
        </div>
    `;
}

registry
    .category("actions")
    .add("mail.link_preview_settings_action", LinkPreviewSettingsClientAction);
