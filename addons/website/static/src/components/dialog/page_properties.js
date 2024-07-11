/** @odoo-module **/

import {CheckBox} from '@web/core/checkbox/checkbox';
import { _t } from "@web/core/l10n/translation";
import {useService, useAutofocus} from "@web/core/utils/hooks";
import {sprintf} from "@web/core/utils/strings";
import {WebsiteDialog} from './dialog';
import {FormViewDialog} from "@web/views/view_dialogs/form_view_dialog";
import { renderToFragment } from "@web/core/utils/render";
import { Component, useEffect, useState, xml, useRef, onMounted } from "@odoo/owl";

export class PageDependencies extends Component {
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
PageDependencies.popoverTemplate = xml`
    <div class="popover o_page_dependencies" role="tooltip">
        <div class="arrow"/>
        <h3 class="popover-header"/>
        <div class="popover-body"/>
    </div>
`;
PageDependencies.template = 'website.PageDependencies';
PageDependencies.props = {
    resIds: Array,
    resModel: String,
    mode: String,
};

export class DeletePageDialog extends Component {
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
DeletePageDialog.components = {
    PageDependencies,
    CheckBox,
    WebsiteDialog
};
DeletePageDialog.template = 'website.DeletePageDialog';
DeletePageDialog.props = {
    resIds: Array,
    resModel: String,
    onDelete: {type: Function, optional: true},
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
            // TODO In master support only multiple pages.
            const pageIds = this.props.pageIds ?? [this.props.pageId];
            for (let count = 0; count < pageIds.length; count++) {
                const name = this.state.name + (count ? ` ${count + 1}` : "");
                const res = await this.orm.call(
                    'website.page',
                    'clone_page',
                    [pageIds[count], name]
                );
                if (!this.props.pageIds) {
                    this.website.goToWebsite({path: res, edition: true});
                }
            }
        }
        this.props.onDuplicate();
    }
}
DuplicatePageDialog.components = {WebsiteDialog};
DuplicatePageDialog.template = "website.DuplicatePageDialog";
DuplicatePageDialog.props = {
    onDuplicate: Function,
    close: Function,
    pageId: Number,
    // If pageIds is defined, pageId is ignored.
    pageIds: { type: Array, element: Number, optional: true },
};

export class PagePropertiesDialog extends FormViewDialog {
    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.orm = useService('orm');
        this.website = useService('website');

        this.viewProps.resId = this.resId;

        // TODO: Remove in master, the `w-100` is causing a button's
        // misalignment on the page properties dialog, this should be
        // replaced by adding extra buttons to the default container in
        // `this.viewProps.buttonTemplate`.
        onMounted(() => {
            this.modalRef.el?.querySelector(".modal-footer .o_cp_buttons")?.classList.remove("w-100");
        });
    }

    get resId() {
        return this.props.resId || (this.website.currentWebsite && this.website.currentWebsite.metadata.mainObject.id);
    }

    clonePage() {
        this.dialog.add(DuplicatePageDialog, {
            pageId: this.resId,
            onDuplicate: () => {
                this.props.close();
                this.props.onClose();
            },
        });
    }

    deletePage() {
        const pageIds = [this.resId];
        this.dialog.add(DeletePageDialog, {
            resIds: pageIds,
            resModel: 'website.page',
            onDelete: async () => {
                await this.orm.unlink("website.page", pageIds);
                this.website.goToWebsite({path: '/'});
                this.props.close();
                this.props.onClose();
            },
        });
    }
}
PagePropertiesDialog.template = 'website.PagePropertiesDialog';
PagePropertiesDialog.props = {
    ...FormViewDialog.props,
    onClose: {type: Function, optional: true},
    resModel: {type: String, optional: true},
};

PagePropertiesDialog.defaultProps = {
    ...FormViewDialog.defaultProps,
    resModel: 'website.page',
    title: _t("Page Properties"),
    size: 'md',
    context: {
        form_view_ref: 'website.website_page_properties_view_form',
    },
    onClose: () => {},
};
