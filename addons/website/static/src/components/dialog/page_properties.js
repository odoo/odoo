/** @odoo-module **/

import {CheckBox} from '@web/core/checkbox/checkbox';
import { _lt } from "@web/core/l10n/translation";
import {useService, useAutofocus} from "@web/core/utils/hooks";
import {sprintf} from "@web/core/utils/strings";
import {useWowlService} from '@web/legacy/utils';
import {WebsiteDialog} from './dialog';
import {FormViewDialog} from "@web/views/view_dialogs/form_view_dialog";
import { qweb } from 'web.core';

const { Component, useEffect, useState, xml, useRef } = owl;

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

        this.action = useRef('action');
        this.sprintf = sprintf;

        useEffect(
            () => {
                this.onWillStart();
            },
            () => []
        );
        this.state = useState({
            dependencies: {},
            depText: "...",
        });
    }

    async onWillStart() {
        // TODO Remove in master: call fetchDependencies in useEffect.
        return this.fetchDependencies();
    }

    // TODO Remove in master: use state from template.
    get dependencies() {
        return this.state.dependencies;
    }

    // TODO Remove in master: use state from template.
    get depText() {
        return this.state.depText;
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
            title: this.env._t("Dependencies"),
            boundary: 'viewport',
            placement: 'right',
            trigger: 'focus',
            content: qweb.render("website.PageDependencies.Tooltip", {
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
            const res = await this.orm.call(
                'website.page',
                'clone_page',
                [this.props.pageId, this.state.name]
            );
            this.website.goToWebsite({path: res, edition: true});
        }
        this.props.onDuplicate();
    }
}
DuplicatePageDialog.components = {WebsiteDialog};
DuplicatePageDialog.template = xml`
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
DuplicatePageDialog.props = {
    onDuplicate: {type: Function, optional: true},
    close: Function,
    pageId: Number,
};

export class PagePropertiesDialog extends FormViewDialog {
    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.orm = useService('orm');
        this.website = useService('website');

        this.viewProps.resId = this.resId;
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
    title: _lt("Page Properties"),
    size: 'md',
    context: {
        form_view_ref: 'website.website_page_properties_view_form',
    },
    onClose: () => {},
};
