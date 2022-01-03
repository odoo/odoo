/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

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
    slots: Object,
};
NewContentElement.defaultProps = {
    status: MODULE_STATUS.INSTALLED,
};

export class NewContentModal extends Component {
    setup() {
        this.user = useService('user');
        this.orm = useService('orm');
        this.rpc = useService('rpc');
        this.dialogs = useService('dialog');
        this.website = useService('website');
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
                    moduleXmlId: 'base.module_website_blog',
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-rss"/>`,
                    title: this.env._t('Blog Post'),
                },
                {
                    moduleXmlId: 'base.module_website_event',
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-ticket"/>`,
                    title: this.env._t('Event'),
                },
                {
                    moduleXmlId: 'base.module_website_forum',
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-comment"/>`,
                    redirectUrl: '/forum',
                    title: this.env._t('Forum'),
                },
                {
                    moduleXmlId: 'base.module_website_hr_recruitment',
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-briefcase"/>`,
                    title: this.env._t('Job Offer'),
                },
                {
                    moduleXmlId: 'base.module_website_sale',
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-shopping-cart"/>`,
                    title: this.env._t('Product'),
                },
                {
                    moduleXmlId: 'base.module_website_slides',
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa module_icon" style="background-image: url('/website/static/src/img/apps_thumbs/website_slide.svg');background-repeat: no-repeat; background-position: center;"/>`,
                    title: this.env._t('Course'),
                },
                {
                    moduleXmlId: 'base.module_website_livechat',
                    status: MODULE_STATUS.NOT_INSTALLED,
                    icon: xml`<i class="fa fa-comments"/>`,
                    title: this.env._t('Livechat Widget'),
                    redirectUrl: '/livechat'
                },
            ]
        });

        onWillStart(async () => {
            this.isDesigner = await this.user.hasGroup('website.group_website_designer');

            const xmlIds = this.state.newContentElements.filter(({status}) => status === MODULE_STATUS.NOT_INSTALLED).map(({moduleXmlId}) => moduleXmlId);

            this.modulesInfo = await this.rpc('/website/get_modules_info', {xml_ids: xmlIds});
        });
    }

    get sortedNewContentElements() {
        return this.state.newContentElements.filter(({status}) => status !== MODULE_STATUS.NOT_INSTALLED).concat(this.state.newContentElements.filter(({status}) => status === MODULE_STATUS.NOT_INSTALLED));
    }

    createNewPage() {}

    async installModule(id, redirectUrl) {
        await this.orm.call(
            'ir.module.module',
            'button_immediate_install',
            [id],
        );
        if (redirectUrl) {
            window.location.replace(redirectUrl);
        } else {
            const { id, metadata: { path } } = this.website.currentWebsite;
            // A reload is needed after installing a new module, to instantiate
            // a NewContentModal with patches from the installed module.
            window.location.replace(`/web#action=website.website_editor&website_id=${id}&path=${path}&display_new_content=true`);
        }
    }

    onClickNewContent(element) {
        if (element.createNewContent) {
            return element.createNewContent();
        }

        const {id, name} = this.modulesInfo[element.moduleXmlId];
        const dialogProps = {
            title: this.env._t("Install"),
            body: _.str.sprintf(this.newContentText.installNeeded, name),
            confirm: async () => {
                // Update the NewContentElement with installing icon and text.
                this.state.newContentElements = this.state.newContentElements.map(el => {
                    if (el.moduleXmlId === element.moduleXmlId) {
                        el.status = MODULE_STATUS.INSTALLING;
                        el.icon = xml`<i class="fa fa-spin fa-circle-o-notch"/>`;
                        el.title = _.str.sprintf(this.newContentText.installPleaseWait, name);
                    }
                    return el;
                });
                try {
                    await this.installModule(id, element.redirectUrl);
                } catch (error) {
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
            cancel: () => {},
        };
        this.dialogs.add(ConfirmationDialog, dialogProps);
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
        this.websiteContext.showNewContentModal = !this.websiteContext.showNewContentModal
    }

    onKeydown(ev) {
        if (this.websiteContext.showNewContentModal && ev.keyCode === 27) {
            this.websiteContext.showNewContentModal = false;
            ev.preventDefault();
            ev.stopPropagation();
        }
    }
}
NewContentSystray.template = "website.NewContentSystray";
NewContentSystray.components = { NewContentModal };

export const systrayItem = {
    Component: NewContentSystray,
};

registry.category("website_systray").add("NewContent", systrayItem, { sequence: 10 });
