/** @odoo-module **/

import {CheckBox} from '@web/core/checkbox/checkbox';
import {useService, useAutofocus} from "@web/core/utils/hooks";
import {useWowlService} from '@web/legacy/utils';
import {WebsiteDialog} from './dialog';
import {FormViewDialog} from "@web/views/view_dialogs/form_view_dialog";
import {qweb, _t} from 'web.core';

const {Component, onWillStart, useState, xml, useRef, markup} = owl;

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
            title: this.env._t("Dependencies"),
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
        this.website.goToWebsite({path: '/'});
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
    pageId: Number,
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
        this.dialog.add(DeletePageDialog, {
            pageId: this.resId,
            onDelete: () => {
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
