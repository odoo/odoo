import { useService } from "@web/core/utils/hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { InstallModuleDialog } from "./install_module_dialog";
import { Component, useState, xml, onWillStart } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { sprintf } from "@web/core/utils/strings";
import { redirect } from "@web/core/utils/urls";

export const MODULE_STATUS = {
    NOT_INSTALLED: "NOT_INSTALLED",
    INSTALLING: "INSTALLING",
    FAILED_TO_INSTALL: "FAILED_TO_INSTALL",
    INSTALLED: "INSTALLED",
};

export class NewContentSystrayItem extends Component {
    static template = "website.NewContentSystrayItem";
    static components = { Dropdown, DropdownItem };
    static props = {
        onNewPage: Function,
    };

    setup() {
        this.website = useService("website");
        this.websiteContext = this.website.context;
        this.dropdown = useState(this.websiteContext.newContentDropdown);
        const openDropdown = this.dropdown.open;
        this.dropdown.open = () => {
            openDropdown();
            this.openDropdown();
        };
        this.dropdownFirstTimeOpened = true;
        this.orm = useService("orm");
        this.dialogs = useService("dialog");
        this.action = useService("action");
        this.isSystem = user.isSystem;
        // useActiveElement("modalRef"); TODO: check if needed

        this.newContentText = {
            failed: _t('Failed to install "%s"'),
            installInProgress: _t("The installation of an App is already in progress."),
            installNeeded: _t('Do you want to install the "%s" App?'),
            installPleaseWait: _t('Installing "%s"'),
        };

        this.state = useState({
            newContentElements: [
                {
                    moduleName: "website_blog",
                    moduleXmlId: "base.module_website_blog",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: "/website_blog/static/description/icon.png",
                    title: _t("Blog Post"),
                    description: _t("Create a new article"),
                },
                {
                    moduleName: "website_event",
                    moduleXmlId: "base.module_website_event",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: "/website_event/static/description/icon.png",
                    title: _t("Event"),
                    description: _t("Create a new event"),
                },
                {
                    moduleName: "website_forum",
                    moduleXmlId: "base.module_website_forum",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: "/website_forum/static/description/icon.png",
                    redirectUrl: "/forum",
                    title: _t("Forum"),
                    description: _t("Create a new forum"),
                },
                {
                    moduleName: "website_hr_recruitment",
                    moduleXmlId: "base.module_website_hr_recruitment",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: "/website_hr_recruitment/static/description/icon.png",
                    title: _t("Job Position"),
                    description: _t("Showcase job offers"),
                },
                {
                    moduleName: "website_sale",
                    moduleXmlId: "base.module_website_sale",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: "/website_sale/static/description/icon.png",
                    title: _t("Product"),
                    description: _t("Create a new product"),
                },
                {
                    moduleName: "website_slides",
                    moduleXmlId: "base.module_website_slides",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: "/website_slides/static/description/icon.png",
                    title: _t("Course"),
                    description: _t("Create a new course"),
                },
                {
                    moduleName: "website_livechat",
                    moduleXmlId: "base.module_website_livechat",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: "/website_livechat/static/description/icon.png",
                    title: _t("Livechat Widget"),
                    description: _t("Allow customers to reach you"),
                },
            ],
        });

        useHotkey("escape", () => {
            if (this.dropdown.isOpen) {
                this.dropdown.close();
            }
        });

        onWillStart(this.onWillStart.bind(this));
    }

    async onWillStart() {
        // TODO: ask if better to have this in onWillStart (reduces number of rpc calls by default, but adds waiting time to remove unauthorized elements when opening dropdown) or in openDropdown (creates race condition actually, so bad idea)
        // TODO: other solution, when clicking on "New" button avoid opening dropdown, first compute this and then open dropdown

        this.isDesigner = await user.hasGroup("website.group_website_designer");
        // TODO: remove isDesigner because not used

        this.canInstall = user.isAdmin;
        if (this.canInstall) {
            const moduleNames = this.state.newContentElements
                .filter(({ status }) => status === MODULE_STATUS.NOT_INSTALLED)
                .map(({ moduleName }) => moduleName);
            this.modulesInfo = {};
            for (const record of await this.orm
                .cached()
                .searchRead(
                    "ir.module.module",
                    [["name", "in", moduleNames]],
                    ["id", "name", "shortdesc"]
                )) {
                this.modulesInfo[record.name] = { id: record.id, name: record.shortdesc };
            }
        }
        const modelsToCheck = [];
        const elementsToUpdate = {};
        for (const element of this.state.newContentElements) {
            if (element.model) {
                modelsToCheck.push(element.model);
                elementsToUpdate[element.model] = element;
            }
        }
        const accesses = await rpc(
            "/website/check_new_content_access_rights",
            {
                models: modelsToCheck,
            },
            { cached: true }
        );
        for (const [model, access] of Object.entries(accesses)) {
            elementsToUpdate[model].isDisplayed = access;
        }
    }

    async openDropdown() {
        if (this.dropdownFirstTimeOpened) {
            this.dropdownFirstTimeOpened = false;
        } else {
            return;
        }

        // preload the new page templates so they are ready as soon as possible
        rpc(
            "/website/get_new_page_templates",
            { context: { website_id: this.website.currentWebsiteId } },
            { cached: true, silent: true }
        );
    }

    get sortedNewContentElements() {
        return this.state.newContentElements
            .filter(({ status }) => status !== MODULE_STATUS.NOT_INSTALLED)
            .concat(
                this.state.newContentElements.filter(
                    ({ status }) => status === MODULE_STATUS.NOT_INSTALLED
                )
            );
    }

    async installModule(id, redirectUrl) {
        await this.orm.silent.call("ir.module.module", "button_immediate_install", [id]);
        if (redirectUrl) {
            this.website.prepareOutLoader();
            redirect(redirectUrl);
        } else {
            const {
                id,
                metadata: { path, viewXmlid },
            } = this.website.currentWebsite;
            const url = new URL(path);
            if (viewXmlid === "website.page_404") {
                url.pathname = "";
            }
            // A reload is needed after installing a new module, to instantiate
            // a NewContentModal with patches from the installed module.
            this.website.prepareOutLoader();
            redirect(
                `/odoo/action-website.website_preview?website_id=${id}&path=${encodeURIComponent(
                    url.toString()
                )}&display_new_content=true`
            );
        }
    }

    onClickNewContent(element) {
        if (element.createNewContent) {
            return element.createNewContent();
        }
        // throw new Error(JSON.stringify({ element, modules: this.modulesInfo }));
        const { id, name } = this.modulesInfo[element.moduleName];
        const dialogProps = {
            title: element.title,
            installationText: sprintf(this.newContentText.installNeeded, name),
            installModule: async () => {
                // Update the NewContentElement with installing icon and text.
                this.state.newContentElements = this.state.newContentElements.map((el) => {
                    if (el.moduleXmlId === element.moduleXmlId) {
                        el.status = MODULE_STATUS.INSTALLING;
                        el.icon = xml`<i class="fa fa-spin fa-circle-o-notch"/>`;
                        el.title = sprintf(this.newContentText.installPleaseWait, name);
                    }
                    return el;
                });
                this.website.showLoader({ title: _t("Building your %s", name) });
                try {
                    await this.installModule(id, element.redirectUrl);
                } catch (error) {
                    this.website.hideLoader();
                    // Update the NewContentElement with failure icon and text.
                    this.state.newContentElements = this.state.newContentElements.map((el) => {
                        if (el.moduleXmlId === element.moduleXmlId) {
                            el.status = MODULE_STATUS.FAILED_TO_INSTALL;
                            el.icon = xml`<i class="fa fa-exclamation-triangle"/>`;
                            el.title = sprintf(this.newContentText.failed, name);
                        }
                        return el;
                    });
                    console.error(error);
                }
            },
        };
        this.dialogs.add(InstallModuleDialog, dialogProps);
    }

    /**
     * This method registers the action to perform when a new content is
     * saved. The path must be computed once the record is saved, to
     * perform the 'ir.act_window_close' action, which will be used when
     * the dialog is closed to go to the correct website page.
     */
    async onAddContent(action, edition = false, context = null) {
        this.action.doAction(action, {
            additionalContext: context ? context : {},
            onClose: (infos) => {
                if (infos && !infos.dismiss) {
                    this.website.goToWebsite({ path: infos.path, edition: edition });
                    this.dropdown.close();
                }
            },
            props: {
                onSave: (record, params) => {
                    if (record.resId) {
                        const path = params.computePath();
                        this.action.doAction({
                            type: "ir.actions.act_window_close",
                            infos: { path },
                        });
                    }
                },
            },
        });
    }
}
