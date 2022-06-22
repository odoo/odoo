/** @odoo-module **/

import {CheckBox} from '@web/core/checkbox/checkbox';
import {useService} from "@web/core/utils/hooks";
import {useWowlService} from '@web/legacy/utils';
import {WebsiteDialog} from './dialog';
import {FormViewDialog} from 'web.view_dialogs';
import {standaloneAdapter} from 'web.OwlCompatibility';
import {qweb} from 'web.core';

const {Component, onWillStart, useState, xml, useRef, markup, onWillRender} = owl;

export class PageDependencies extends Component {
    setup() {
        super.setup();
        try {
            this.orm = useService('orm');
        } catch {
            // We are in a legacy environment.
            // TODO check with framework team to know if this is really needed.
            this.orm = useWowlService('orm');
        }

        this.dependencies = {};
        this.depText = '...';
        this.action = useRef('action');

        onWillStart(() => this.onWillStart());
    }

    async onWillStart() {
        this.dependencies = await this.orm.call(
            'website',
            this.props.type === 'key' ?
                'page_search_key_dependencies' :
                'page_search_dependencies',
            [this.props.pageId],
        );
        if (this.props.mode === 'popover') {
            this.depText = Object.entries(this.dependencies)
                .map(dependency => `${dependency[1].length} ${dependency[0].toLowerCase()}`)
                .join(', ');
        } else {
            for (const key of Object.keys(this.dependencies)) {
                this.dependencies[key] = this.dependencies[key].map(item => {
                    // TODO probably need to refactor this feature so that the
                    // client side is in charge of what the sentences look like
                    // (not server-side HTML).
                    item.contentToDisplay = markup(item.content);
                    return item;
                });
            }
        }
    }

    showDependencies() {
        $(this.action.el).popover({
            title: this.env._t('Dependencies'),
            boundary: 'viewport',
            placement: 'right',
            trigger: 'focus',
            content: qweb.render('website.PageDependencies.Tooltip', {dependencies: this.dependencies}),
        }).popover('toggle');
    }
}
PageDependencies.popoverTemplate = xml`
    <div class="popover o_page_dependencies" role="tooltip">
        <div class="arrow"/>
        <h3 class="popover-header"/>
        <div class="popover-body"/>
    </div>
`;
PageDependencies.template = 'website.PageDependencies';
PageDependencies.props = {
    pageId: Number,
    mode: String,
    type: {
        type: String,
        optional: true,
    },
};

export class DeletePageDialog extends WebsiteDialog {
    setup() {
        super.setup();

        this.orm = useService('orm');
        this.website = useService('website');
        this.title = this.env._t("Delete Page");
        this.primaryTitle = this.env._t("Ok");

        this.state = useState({
            confirm: false,
        });
    }

    onConfirmCheckboxChange(checked) {
        this.state.confirm = checked;
    }

    async primaryClick() {
        await this.orm.unlink("website.page", [
            this.props.pageId,
        ]);
        this.website.goToWebsite();
        this.close();
        this.props.onClose();
    }
}
DeletePageDialog.components = {PageDependencies, CheckBox};
DeletePageDialog.bodyTemplate = 'website.DeletePageContent';
DeletePageDialog.footerTemplate = 'website.DeletePageAction';
DeletePageDialog.props = {
    ...WebsiteDialog.props,
    pageId: Number,
    onClose: Function,
};

export class DuplicatePageDialog extends WebsiteDialog {
    setup() {
        super.setup();

        this.orm = useService('orm');
        this.website = useService('website');

        this.state = useState({
            name: '',
        });
    }

    async primaryClick() {
        if (this.state.name) {
            const res = await this.orm.call(
                'website.page',
                'clone_page',
                [this.props.pageId, this.state.name]
            );
            this.website.goToWebsite({path: res, edition: true});
        }
        this.close();
        this.props.onClose();
    }
}
DuplicatePageDialog.bodyTemplate = xml`
    <div class="form-group row">
        <label class="col-form-label col-md-3">
            Page Name
        </label>
        <div class="col-md-9">
            <input type="text" t-model="state.name" class="form-control" required="required"/>
        </div>
    </div>
`;
DuplicatePageDialog.props = {
    ...WebsiteDialog.props,
    onClose: Function,
};

export class PagePropertiesDialogWrapper extends Component {
    setup() {
        try {
            this.websiteService = useService('website');
            this.dialogService = useService('dialog');
            this.orm = useService('orm');
        } catch {
            // Use services in legacy environment.
            this.websiteService = useWowlService('website');
            this.dialogService = useWowlService('dialog');
            this.orm = useWowlService('orm');
        }

        onWillRender(this.setDialogWidget);
    }

    createDialog() {
        if (this.props.mode === 'clone') {
            return {
                component: DuplicatePageDialog,
                open: () => this.dialogService.add(DuplicatePageDialog, {
                    pageId: this.pageId,
                    onClose: this.props.onClose,
                }),
            };
        } else if (this.props.mode === 'delete') {
            return {
                component: DeletePageDialog,
                open: () => this.dialogService.add(DeletePageDialog, {
                    pageId: this.pageId,
                    onClose: this.props.onClose,
                }),
            };
        } else {
            const parent = standaloneAdapter({Component});
            const formViewDialog = new FormViewDialog(parent, this.dialogOptions);
            formViewDialog.buttons = [...formViewDialog.buttons, ...this.extraButtons];
            formViewDialog.on('form_dialog_discarded', parent, this.setDialogWidget.bind(this));
            return formViewDialog;
        }
    }

    get pageId() {
        return this.props.currentPage || (this.websiteService.currentWebsite && this.websiteService.currentWebsite.metadata.mainObject.id);
    }

    get dialogOptions() {
        return {
            res_model: "website.page",
            res_id: this.pageId,
            context: {
                form_view_ref: 'website.website_page_properties_view_form'
            },
            title: this.env._t("Page Properties"),
            size: 'medium',
            on_saved: (record, changed) => {
                if (changed) {
                    return this.orm.read("website.page", [this.pageId], ['url']).then(res => {
                        this.websiteService.goToWebsite({websiteId: record.data.website_id.res_id, path: res[0]['url']});
                    });
                }
            },
        };
    }

    get extraButtons() {
        const wrapper = this;
        return [{
            text: this.env._t("Duplicate Page"),
            icon: 'fa-clone',
            classes: 'btn-link ml-auto',
            click: function () {
                wrapper.dialogService.add(DuplicatePageDialog, {
                    pageId: wrapper.pageId,
                    onClose: this.close.bind(this),
                });
            },
        },
        {
            text: this.env._t("Delete Page"),
            icon: 'fa-trash',
            classes: 'btn-link',
            click: function () {
                wrapper.dialogService.add(DeletePageDialog, {
                    pageId: wrapper.pageId,
                    onClose: this.close.bind(this),
                });
            },
        }];
    }

    setDialogWidget() {
        this.props.setPagePropertiesDialog(this.createDialog());
    }
}
PagePropertiesDialogWrapper.template = xml``;
PagePropertiesDialogWrapper.props = {
    setPagePropertiesDialog: Function,
    onClose: {
        type: Function,
        optional: true,
    },
    currentPage: {
        type: Number,
        optional: true,
    },
    mode: {
        type: String,
        optional: true,
    },
};
