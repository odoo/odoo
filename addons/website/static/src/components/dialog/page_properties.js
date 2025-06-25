import {CheckBox} from '@web/core/checkbox/checkbox';
import { _t } from "@web/core/l10n/translation";
import {useService, useAutofocus} from "@web/core/utils/hooks";
import {sprintf} from "@web/core/utils/strings";
import {WebsiteDialog} from './dialog';
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import {FormViewDialog} from "@web/views/view_dialogs/form_view_dialog";
import { formView } from '@web/views/form/form_view';
import { renderToFragment } from "@web/core/utils/render";
import { Component, onWillDestroy, useEffect, useRef, useState, xml } from "@odoo/owl";
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
        });

        onWillDestroy(async () => {
            await this.destroyDependenciesPopover();
        });
    }

    async getResIds() {
        return this.props.resIds;
    }

    async fetchDependencies() {
        this.state.dependencies = await this.orm.call(
            'website',
            'search_url_dependencies',
            [this.props.resModel, await this.getResIds()],
        );
    }

    showDependencies() {
        const popover = window.Popover.getOrCreateInstance(this.action.el, {
            title: _t("Dependencies"),
            boundary: 'viewport',
            placement: 'right',
            trigger: 'focus',
            content: () => {
                return renderToFragment("website.PageDependencies.Tooltip", {
                    dependencies: this.state.dependencies,
                });
            },
        });
        popover.toggle();
    }

    async destroyDependenciesPopover() {
        const actionEl = this.action.el;
        const popover = window.Popover.getInstance(actionEl);
        if (popover) {
            // If popover is hiding (animation), wait for the animation to
            // complete.
            if (!popover.tip.classList.contains("show")) {
                await new Promise((resolve) => {
                    const handler = () => {
                        actionEl.removeEventListener("hidden.bs.popover", handler);
                        resolve();
                    };
                    actionEl.addEventListener("hidden.bs.popover", handler);
                });
            }
            popover.dispose();
        }
    }
}

export class FormPageDependencies extends PageDependencies {
    static props = {
        ...standardFieldProps,
        ...PageDependencies.props,
        resIds: { type: Array, optional: true },
    };

    async getResIds() {
        const records = await this.orm.read(
            this.props.record.resModel,
            [this.props.record.resId],
            ["target_model_id"],
        );
        return records.map((record) => record.target_model_id[0]);
    }
}

export const formPageDependenciesWidget = {
    component: FormPageDependencies,
    extractProps: ({ attrs }) => {
        const { mode, name, resModel, resIds } = attrs;
        return {
            mode,
            name: name || "",
            resModel,
            resIds,
        };
    },
};
registry.category("view_widgets").add("form_page_dependencies", formPageDependenciesWidget);

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
    static template = "website.DuplicatePageDialog";
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
        clonePage: { type: Function, optional: true },
        deletePage: { type: Function, optional: true },
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
        title: _t("Page Properties"),
        size: "md",
        onClose: () => {},
    };

    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.orm = useService('orm');
        this.website = useService('website');

        this.viewProps = {
            ...this.viewProps,
            resId: this.resId,
            resModel: this.resModel,
            context: Object.assign(
                {
                    form_view_ref: this.isPage
                        ? "website.website_page_properties_view_form"
                        : "website.website_page_properties_base_view_form",
                },
                this.viewProps.context,
            ),
            ...(this.isPage
                ? {
                      buttonTemplate: "website.PagePropertiesDialogButtons",
                      clonePage: this.clonePage.bind(this),
                      deletePage: this.deletePage.bind(this),
                  }
                : {}),
        };
    }

    get resId() {
        return this.props.resId;
    }

    get resModel() {
        if (this.props.resModel) {
            return this.props.resModel;
        }
        return this.isPage ? "website.page.properties" : "website.page.properties.base";
    }

    get targetId() {
        return this.website.currentWebsite?.metadata.mainObject.id;
    }

    get targetModel() {
        return this.website.currentWebsite?.metadata.mainObject.model;
    }

    get isPage() {
        return this.targetModel === "website.page";
    }

    clonePage() {
        this.dialog.add(DuplicatePageDialog, {
            pageIds: [this.targetId],
            onDuplicate: (duplicates) => {
                this.props.close();
                this.props.onClose();
                this.website.goToWebsite({ path: duplicates[0], edition: true });
            },
        });
    }

    async deletePage() {
        const pageIds = [this.targetId];
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
