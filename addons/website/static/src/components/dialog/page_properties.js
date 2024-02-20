/** @odoo-module **/

import {CheckBox} from '@web/core/checkbox/checkbox';
import { _t } from "@web/core/l10n/translation";
import {useService, useAutofocus} from "@web/core/utils/hooks";
import {sprintf} from "@web/core/utils/strings";
import {WebsiteDialog} from './dialog';
import {FormViewDialog} from "@web/views/view_dialogs/form_view_dialog";
import { formView } from '@web/views/form/form_view';
import { renderToFragment } from "@web/core/utils/render";
import { Component, useEffect, useState, xml, useRef } from "@odoo/owl";
import { FormController } from '@web/views/form/form_controller';
import { registry } from "@web/core/registry";

export class PageDependencies extends Component {
    static template = "website.PageDependencies";
    static popoverTemplate = xml`
        <div class="popover o_page_dependencies" role="tooltip">
            <div class="arrow"/>
            <h3 class="popover-header"/>
            <div class="popover-body"/>
        </div>
    `;
    static props = {
        resIds: Array,
        resModel: String,
        mode: String,
    };

    setup() {
        super.setup();
        this.orm = useService('orm');

        this.action = useRef('action');
        this.sprintf = sprintf;

        useEffect(
            () => {
                this.fetchDependencies();
            },
            () => []
        );
        this.state = useState({
            dependencies: {},
            depText: "...",
        });
    }

    async fetchDependencies() {
        this.state.dependencies = await this.orm.call(
            'website',
            'search_url_dependencies',
            [this.props.resModel, this.props.resIds],
        );
        if (this.props.mode === 'popover') {
            this.state.depText = Object.entries(this.state.dependencies)
                .map(dependency => `${dependency[1].length} ${dependency[0].toLowerCase()}`)
                .join(', ');
        }
    }

    showDependencies() {
        $(this.action.el).popover({
            title: _t("Dependencies"),
            boundary: 'viewport',
            placement: 'right',
            trigger: 'focus',
            content: renderToFragment("website.PageDependencies.Tooltip", {
                dependencies: this.state.dependencies,
            }),
        }).popover('toggle');
    }
}

export class DeletePageDialog extends Component {
    static template = "website.DeletePageDialog";
    static components = {
        PageDependencies,
        CheckBox,
        WebsiteDialog,
    };
    static props = {
        resIds: Array,
        resModel: String,
        onDelete: { type: Function, optional: true },
        close: Function,
        hasNewPageTemplate: { type: Boolean, optional: true },
    };

    setup() {
        this.website = useService('website');
        this.title = _t("Delete Page");
        this.deleteButton = _t("Ok");
        this.cancelButton = _t("Cancel");

        this.state = useState({
            confirm: false,
        });
    }

    onConfirmCheckboxChange(checked) {
        this.state.confirm = checked;
    }

    onClickDelete() {
        this.props.close();
        this.props.onDelete();
    }
}

export class DuplicatePageDialog extends Component {
    static components = { WebsiteDialog };
    static template = xml`
    <WebsiteDialog close="props.close" primaryClick="() => this.duplicate()">
        <div class="mb-3 row">
            <label class="col-form-label col-md-3">
                Page Name
            </label>
            <div class="col-md-9">
                <input type="text" t-model="state.name" class="form-control" required="required" t-ref="autofocus"/>
            </div>
        </div>
    </WebsiteDialog>
    `;
    static props = {
        onDuplicate: Function,
        close: Function,
        pageIds: { type: Array, element: Number },
    };

    setup() {
        this.orm = useService('orm');
        this.website = useService('website');
        useAutofocus();

        this.state = useState({
            name: '',
        });
    }

    async duplicate() {
        const duplicates = [];
        if (this.state.name) {
            for (let count = 0; count < this.props.pageIds.length; count++) {
                const name = this.state.name + (count ? ` ${count + 1}` : "");
                duplicates.push(await this.orm.call(
                    'website.page',
                    'clone_page',
                    [this.props.pageIds[count], name]
                ));
            }
        }
        this.props.onDuplicate(duplicates);
    }
}

export class PagePropertiesFormController extends FormController {
    static props = {
        ...FormController.props,
        clonePage: Function,
        deletePage: Function,
    };
}

registry.category("views").add("page_properties_dialog_form", {
    ...formView,
    Controller: PagePropertiesFormController,
});

export class PagePropertiesDialog extends FormViewDialog {
    static props = {
        ...FormViewDialog.props,
        onClose: { type: Function, optional: true },
        resModel: { type: String, optional: true },
    };

    static defaultProps = {
        ...FormViewDialog.defaultProps,
        resModel: "website.page",
        title: _t("Page Properties"),
        size: "md",
        context: {
            form_view_ref: "website.website_page_properties_view_form",
        },
        onClose: () => {},
    };

    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.orm = useService('orm');
        this.website = useService('website');

        this.viewProps = {
            ...this.viewProps,
            type: "page_properties_dialog_form",
            resId: this.resId,
            buttonTemplate: "website.PagePropertiesDialogButtons",
            clonePage: this.clonePage.bind(this),
            deletePage: this.deletePage.bind(this),
        };
    }

    get resId() {
        return this.props.resId || (this.website.currentWebsite && this.website.currentWebsite.metadata.mainObject.id);
    }

    clonePage() {
        this.dialog.add(DuplicatePageDialog, {
            pageIds: [this.resId],
            onDuplicate: (duplicates) => {
                this.props.close();
                this.props.onClose();
                this.website.goToWebsite({ path: duplicates[0], edition: true });
            },
        });
    }

    async deletePage() {
        const pageIds = [this.resId];
        const newPageTemplateFields = await this.orm.read("website.page", pageIds, ["is_new_page_template"]);
        this.dialog.add(DeletePageDialog, {
            resIds: pageIds,
            resModel: 'website.page',
            onDelete: async () => {
                await this.orm.unlink("website.page", pageIds);
                this.website.goToWebsite({path: '/'});
                this.props.close();
                this.props.onClose();
            },
            hasNewPageTemplate: newPageTemplateFields[0].is_new_page_template,
        });
    }
}
