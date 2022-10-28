/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { WebsiteDialog, AddPageDialog } from "@website/components/dialog/dialog";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { sprintf } from '@web/core/utils/strings';

const { Component, xml, useState, onWillStart } = owl;

export const MODULE_STATUS = {
    NOT_INSTALLED: 'NOT_INSTALLED',
    INSTALLING: 'INSTALLING',
    FAILED_TO_INSTALL: 'FAILED_TO_INSTALL',
    INSTALLED: 'INSTALLED',
};

class NewContentElement extends Component {
    setup() {
        this.MODULE_STATUS = MODULE_STATUS;
    }

    onClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.props.onClick();
    }
}
NewContentElement.template = "website.NewContentElement";
NewContentElement.props = {
    name: { type: String, optional: true },
    title: String,
    onClick: Function,
    status: { type: String, optional: true },
    moduleXmlId: { type: String, optional: true },
    slots: Object,
};
NewContentElement.defaultProps = {
    status: MODULE_STATUS.INSTALLED,
};

class InstallModuleDialog extends Component {
    setup() {
        this.installButton = this.env._t("Install");
    }

    onClickInstall() {
        this.props.close();
        this.props.installModule();
    }
}
InstallModuleDialog.components = { WebsiteDialog };
InstallModuleDialog.template = "website.InstallModuleDialog";

export class NewContentModal extends Component {
    setup() {
        this.user = useService('user');
        this.orm = useService('orm');
        this.rpc = useService('rpc');
        this.dialogs = useService('dialog');
        this.website = useService('website');
        this.action = useService('action');
        this.isSystem = this.user.isSystem;

        this.newContentText = {
            failed: this.env._t('Failed to install "%s"'),
            installInProgress: this.env._t("The installation of an App is already in progress."),
            installNeeded: this.env._t('Do you want to install the "%s" App?'),
            installPleaseWait: this.env._t('Installing "%s"'),
        };

        this.state = useState({
            newContentElements: [
                {
                    moduleName: 'website_blog',
                    moduleXmlId: 'base.module_website_blog',
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-rss"/>`,
                    title: this.env._t('Blog Post'),
                },
                {
                    moduleName: 'website_event',
                    moduleXmlId: 'base.module_website_event',
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-ticket"/>`,
                    title: this.env._t('Event'),
                },
                {
                    moduleName: 'website_forum',
                    moduleXmlId: 'base.module_website_forum',
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-comment"/>`,
                    redirectUrl: '/forum',
                    title: this.env._t('Forum'),
                },
                {
                    moduleName: 'website_hr_recruitment',
                    moduleXmlId: 'base.module_website_hr_recruitment',
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-briefcase"/>`,
                    title: this.env._t('Job Position'),
                },
                {
                    moduleName: 'website_sale',
                    moduleXmlId: 'base.module_website_sale',
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-shopping-cart"/>`,
                    title: this.env._t('Product'),
                },
                {
                    moduleName: 'website_slides',
                    moduleXmlId: 'base.module_website_slides',
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa module_icon" style="background-image: url('/website/static/src/img/apps_thumbs/website_slide.svg');background-repeat: no-repeat; background-position: center;"/>`,
                    title: this.env._t('Course'),
                },
                {
                    moduleName: 'website_livechat',
                    moduleXmlId: 'base.module_website_livechat',
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-comments"/>`,
                    title: this.env._t('Livechat Widget'),
                    redirectUrl: '/livechat'
                },
            ]
        });

        this.websiteContext = useState(this.website.context);
        useHotkey('escape', () => {
            if (this.websiteContext.showNewContentModal) {
                this.websiteContext.showNewContentModal = false;
            }
        });

        onWillStart(this.onWillStart.bind(this));
    }

    async onWillStart() {
        this.isDesigner = await this.user.hasGroup('website.group_website_designer');
        this.canInstall = await this.user.isAdmin;
        if (this.canInstall) {
            const moduleNames = this.state.newContentElements.filter(({status}) => status === MODULE_STATUS.NOT_INSTALLED).map(({moduleName}) => moduleName);
            this.modulesInfo = {};
            for (const record of await this.orm.searchRead(
                "ir.module.module",
                [['name', 'in', moduleNames]],
                ["id", "name", "shortdesc"],
            )) {
                this.modulesInfo[record.name] = {id: record.id, name: record.shortdesc};
            }
        }
    }

    get sortedNewContentElements() {
        return this.state.newContentElements.filter(({status}) => status !== MODULE_STATUS.NOT_INSTALLED).concat(this.state.newContentElements.filter(({status}) => status === MODULE_STATUS.NOT_INSTALLED));
    }

    createNewPage() {
        this.dialogs.add(AddPageDialog, {
            onAddPage: () => this.websiteContext.showNewContentModal = false,
        });
    }

    async installModule(id, redirectUrl) {
        await this.orm.silent.call(
            'ir.module.module',
            'button_immediate_install',
            [id],
        );
        if (redirectUrl) {
            window.location.replace(redirectUrl);
        } else {
            const { id, metadata: { path, viewXmlid } } = this.website.currentWebsite;
            const url = new URL(path);
            if (viewXmlid === 'website.page_404') {
                url.pathname = '';
            }
            // A reload is needed after installing a new module, to instantiate
            // a NewContentModal with patches from the installed module.
            window.location.replace(`/web#action=website.website_preview&website_id=${id}&path=${encodeURIComponent(url.toString())}&display_new_content=true`);
        }
    }

    onClickNewContent(element) {
        if (element.createNewContent) {
            return element.createNewContent();
        }

        const {id, name} = this.modulesInfo[element.moduleName];
        const dialogProps = {
            title: element.title,
            installationText: _.str.sprintf(this.newContentText.installNeeded, name),
            installModule: async () => {
                // Update the NewContentElement with installing icon and text.
                this.state.newContentElements = this.state.newContentElements.map(el => {
                    if (el.moduleXmlId === element.moduleXmlId) {
                        el.status = MODULE_STATUS.INSTALLING;
                        el.icon = xml`<i class="fa fa-spin fa-circle-o-notch"/>`;
                        el.title = _.str.sprintf(this.newContentText.installPleaseWait, name);
                    }
                    return el;
                });
                this.website.showLoader({
                    title: sprintf(this.env._t("Building your %s"), name),
                });
                try {
                    await this.installModule(id, element.redirectUrl);
                } catch (error) {
                    this.website.hideLoader();
                    // Update the NewContentElement with failure icon and text.
                    this.state.newContentElements = this.state.newContentElements.map(el => {
                        if (el.moduleXmlId === element.moduleXmlId) {
                            el.status = MODULE_STATUS.FAILED_TO_INSTALL;
                            el.icon = xml`<i class="fa fa-exclamation-triangle"/>`;
                            el.title = _.str.sprintf(this.newContentText.failed, name);
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
    async onAddContent(action, edition = false) {
        this.action.doAction(action, {
            onClose: (infos) => {
                if (infos) {
                    this.website.goToWebsite({ path: infos.path, edition: edition });
                }
            },
            props: {
                onSave: (record, params) => {
                    if (record.resId) {
                        const path = params.computePath();
                        this.action.doAction({
                            type: "ir.actions.act_window_close",
                            infos: { path }
                        });
                    }
                }
            }
        });
    }
}
NewContentModal.template = "website.NewContentModal";
NewContentModal.components = { NewContentElement };

class NewContentSystray extends Component {
    setup() {
        this.rpc = useService('rpc');
        this.website = useService('website');
        this.websiteContext = useState(this.website.context);
    }

    onClick() {
        this.websiteContext.showNewContentModal = !this.websiteContext.showNewContentModal;
    }
}
NewContentSystray.template = "website.NewContentSystray";
NewContentSystray.components = { NewContentModal };

export const systrayItem = {
    Component: NewContentSystray,
};

registry.category("website_systray").add("NewContent", systrayItem, { sequence: 10 });
