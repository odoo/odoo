import { InstallModuleDialog } from "./install_module_dialog";
import { MODULE_STATUS, NewContentElement } from "./new_content_element";
import { Component, onWillStart, useState, xml } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useActiveElement } from "@web/core/ui/ui_service";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { redirect } from "@web/core/utils/urls";

export class NewContentModal extends Component {
    static template = "website.NewContentModal";
    static components = { NewContentElement };
    static props = {
        onNewPage: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.dialogs = useService("dialog");
        this.website = useService("website");
        // Preload the new page templates so they are ready as soon as possible.
        // Do not cache here to avoid stale results when templates change
        // (e.g., toggling "Is a Template" in page properties during a session).
        rpc(
            "/website/get_new_page_templates",
            { context: { website_id: this.website.currentWebsiteId } },
            { silent: true }
        );
        this.action = useService("action");
        this.isSystem = user.isSystem;
        useActiveElement("modalRef");

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
                    icon: xml`<i class="fa fa-newspaper-o"/>`,
                    title: _t("Blog Post"),
                },
                {
                    moduleName: "website_event",
                    moduleXmlId: "base.module_website_event",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-ticket"/>`,
                    title: _t("Event"),
                },
                {
                    moduleName: "website_forum",
                    moduleXmlId: "base.module_website_forum",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-comment"/>`,
                    redirectUrl: "/forum",
                    title: _t("Forum"),
                },
                {
                    moduleName: "website_hr_recruitment",
                    moduleXmlId: "base.module_website_hr_recruitment",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-briefcase"/>`,
                    title: _t("Job Position"),
                },
                {
                    moduleName: "website_sale",
                    moduleXmlId: "base.module_website_sale",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-shopping-cart"/>`,
                    title: _t("Product"),
                },
                {
                    moduleName: "website_slides",
                    moduleXmlId: "base.module_website_slides",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa module_icon" style="background-image: url('/website/static/src/img/apps_thumbs/website_slide.svg');background-repeat: no-repeat; background-position: center;"/>`,
                    title: _t("Course"),
                },
                {
                    moduleName: "website_livechat",
                    moduleXmlId: "base.module_website_livechat",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-comments"/>`,
                    title: _t("Livechat Widget"),
                },
            ],
        });

        this.websiteContext = useState(this.website.context);
        useHotkey("escape", () => {
            if (this.websiteContext.showNewContentModal) {
                this.websiteContext.showNewContentModal = false;
            }
        });

        onWillStart(this.onWillStart.bind(this));
    }

    async onWillStart() {
        this.isDesigner = await user.hasGroup("website.group_website_designer");
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
            window.location.replace(redirectUrl);
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
                    this.websiteContext.showNewContentModal = false;
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
