/** @odoo-module **/

import {CheckBox} from '@web/core/checkbox/checkbox';
import {useService, useAutofocus} from "@web/core/utils/hooks";
import {useWowlService} from '@web/legacy/utils';
import {WebsiteDialog} from './dialog';
import {FormViewDialog} from 'web.view_dialogs';
import {standaloneAdapter} from 'web.OwlCompatibility';
import {qweb} from 'web.core';

const {Component, onWillStart, useState, xml, useRef, markup, onRendered} = owl;

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

export class DeletePageDialog extends Component {
    setup() {
        this.orm = useService('orm');
        this.website = useService('website');
        this.title = this.env._t("Delete Page");
        this.deleteButton = this.env._t("Ok");
        this.cancelButton = this.env._t("Cancel");

        this.state = useState({
            confirm: false,
        });
    }

    onConfirmCheckboxChange(checked) {
        this.state.confirm = checked;
    }

    async onClickDelete() {
        await this.orm.unlink("website.page", [
            this.props.pageId,
        ]);
        this.website.goToWebsite();
        this.props.close();
        this.props.onClose();
    }
}
DeletePageDialog.components = {
    PageDependencies,
    CheckBox,
    WebsiteDialog
};
DeletePageDialog.template = 'website.DeletePageDialog';
DeletePageDialog.props = {
    pageId: Number,
    onClose: Function,
    close: Function,
};

export class DuplicatePageDialog extends Component {
    setup() {
        this.orm = useService('orm');
        this.website = useService('website');
        useAutofocus();

        this.state = useState({
            name: '',
        });
    }

    async duplicate() {
        if (this.state.name) {
            const res = await this.orm.call(
                'website.page',
                'clone_page',
                [this.props.pageId, this.state.name]
            );
            this.website.goToWebsite({path: res, edition: true});
        }
        this.props.onClose();
    }
}
DuplicatePageDialog.components = {WebsiteDialog};
DuplicatePageDialog.template = xml`
<WebsiteDialog close="props.close" primaryClick="() => this.duplicate()">
    <div class="form-group row">
        <label class="col-form-label col-md-3">
            Page Name
        </label>
        <div class="col-md-9">
            <input type="text" t-model="state.name" class="form-control" required="required" t-ref="autofocus"/>
        </div>
    </div>
</WebsiteDialog>
`;
DuplicatePageDialog.props = {
    onClose: Function,
    close: Function,
    pageId: Number,
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

        onRendered(this.createDialog);
    }

    createDialog() {
        if (this.props.mode === 'clone') {
            this.dialogService.add(DuplicatePageDialog, {
                pageId: this.pageId,
                onClose: this.props.onClose,
            });
        } else if (this.props.mode === 'delete') {
            this.dialogService.add(DeletePageDialog, {
                pageId: this.pageId,
                onClose: this.props.onClose,
            });
        } else {
            const parent = standaloneAdapter({Component});
            const formViewDialog = new FormViewDialog(parent, this.dialogOptions);
            formViewDialog.buttons = [...formViewDialog.buttons, ...this.extraButtons];
            formViewDialog.on('form_dialog_discarded', parent, () => this.websiteService.context.showPageProperties = false);
            formViewDialog.open();
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
            classes: 'btn-link ms-auto',
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
}
PagePropertiesDialogWrapper.template = xml``;
PagePropertiesDialogWrapper.props = {
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
