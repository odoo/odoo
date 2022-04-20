/** @odoo-module **/

import {Switch} from '@website/components/switch/switch';
import AbstractFieldOwl from 'web.AbstractFieldOwl';
import fieldRegistry from 'web.field_registry_owl';
import {useService} from "@web/core/utils/hooks";
import {useWowlService} from '@web/legacy/utils';
import {WebsiteDialog} from './dialog';
import {FormViewDialog} from 'web.view_dialogs';
import {standaloneAdapter} from 'web.OwlCompatibility';
import {qweb} from 'web.core';

const {CheckBox} = require("@web/core/checkbox/checkbox");
const {Component, onWillStart, useState, xml, useRef, markup, onWillRender} = owl;

class PageDependencies extends Component {
    setup() {
        super.setup();
        try {
            this.orm = useService('orm');
        } catch (e) {
            // We are in a legacy environment.
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
            'page_search_dependencies',
            [this.props.pageId]
        );
        if (this.props.mode === 'popover') {
            this.depText = Object.entries(this.dependencies)
                .map(dependency => `${dependency[1].length} ${dependency[0].toLowerCase()}`)
                .join(', ');
        } else {
            for (const key of Object.keys(this.dependencies)) {
                this.dependencies[key] = this.dependencies[key].map(item => {
                    item.text = markup(item.text);
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
            this.website.goToWebsite({path: res});
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
        super.setup();
        this.websiteService = useService('website');
        this.dialogService = useService('dialog');

        onWillRender(this.setDialogWidget);
    }

    createDialogWidget() {
        const parent = standaloneAdapter({Component});
        const formViewDialog = new FormViewDialog(parent, this.dialogOptions);
        formViewDialog.buttons = [...formViewDialog.buttons, ...this.dialogOptions.extraButtons];
        formViewDialog.on('form_dialog_discarded', parent, this.setDialogWidget.bind(this));
        return formViewDialog;
    }

    get pageId() {
        return this.websiteService.currentWebsite && this.websiteService.currentWebsite.metadata.mainObject.id;
    }

    get dialogOptions() {
        const wrapper = this;
        return {
            res_model: "website.page",
            res_id: this.pageId,
            context: {
                form_view_ref: 'website.website_page_properties_view_form'
            },
            title: this.env._t("Page Properties"),
            size: 'medium',
            on_saved: (record) => this.websiteService.goToWebsite({path: record.data.url}),
            extraButtons: [{
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
            }],
        };
    }

    setDialogWidget() {
        this.props.setPagePropertiesDialog(this.createDialogWidget());
    }
}
PagePropertiesDialogWrapper.template = xml`<t/>`;

class FieldPageUrl extends AbstractFieldOwl {
    setup() {
        super.setup();

        this.state = useState({
            redirectOldUrl: false,
            url: this.value,
            redirectType: '301',
        });

        this.serverUrl = window.location.origin;
        this.pageUrl = this.value;
    }

    get enableRedirect() {
        return this.state.url !== this.pageUrl;
    }

    onChangeRedirectOldUrl(value) {
        this.state.redirectOldUrl = value;
    }

    /**
     * @override
     */
    commitChanges() {
        if (this.enableRedirect) {
            this._setValue(this.state.url);
            if (this.state.redirectOldUrl) {
                return this.rpc({
                    model: 'website.rewrite',
                    method: 'create',
                    args: [{
                        'name': this.recordData.name,
                        'redirect_type': this.state.redirectType,
                        'url_from': this.pageUrl,
                        'url_to': this.state.url,
                        'website_id': this.recordData.website_id.res_id,
                    }],
                });
            }
        }
        return super.commitChanges();
    }
}
FieldPageUrl.components = {Switch, PageDependencies};
FieldPageUrl.supportedFieldTypes = ['char'];
FieldPageUrl.template = 'website.FieldPageUrl';

fieldRegistry.add('page_url', FieldPageUrl);
