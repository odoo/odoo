/** @odoo-module **/

import {
    Many2ManyTagsField,
    Many2ManyTagsFieldColorEditable,
} from "@web/views/fields/many2many_tags/many2many_tags_field";

import {Dialog} from "@web/core/dialog/dialog";
import {FormController} from "@web/views/form/form_controller";
import {FormViewDialog} from "@web/views/view_dialogs/form_view_dialog";
import {Many2OneAvatarField} from "@web/views/fields/many2one_avatar/many2one_avatar_field";
import {Many2OneBarcodeField} from "@web/views/fields/many2one_barcode/many2one_barcode_field";
import {Many2OneField} from "@web/views/fields/many2one/many2one_field";
import {ReferenceField} from "@web/views/fields/reference/reference_field";
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {isX2Many} from "@web/views/utils";
import {is_option_set} from "@web_m2x_options/components/relational_utils.esm";
import {patch} from "@web/core/utils/patch";
import {sprintf} from "@web/core/utils/strings";
import {useService} from "@web/core/utils/hooks";

const {Component} = owl;

/**
 *  Patch Many2ManyTagsField
 **/
patch(Many2ManyTagsField.prototype, "web_m2x_options.Many2ManyTagsField", {
    setup() {
        this._super(...arguments);
        this.actionService = useService("action");
    },
    /**
     * @override
     */
    getTagProps(record) {
        const props = this._super(...arguments);
        props.onClick = (ev) => this.onMany2ManyBadgeClick(ev, record);
        return props;
    },
    async onMany2ManyBadgeClick(event, record) {
        var self = this;
        if (self.props.open) {
            var context = self.context;
            var id = record.data.id;
            if (self.props.readonly) {
                event.preventDefault();
                event.stopPropagation();
                const action = await self.orm.call(
                    self.props.relation,
                    "get_formview_action",
                    [[id]],
                    {context: context}
                );
                self.actionService.doAction(action);
            } else {
                const view_id = await self.orm.call(
                    self.props.relation,
                    "get_formview_id",
                    [[id]],
                    {context: context}
                );

                const write_access = await self.orm.call(
                    self.props.relation,
                    "check_access_rights",
                    [],
                    {operation: "write", raise_exception: false}
                );
                var can_write = self.props.canWrite;
                self.dialog.add(FormViewDialog, {
                    resModel: self.props.relation,
                    resId: id,
                    context: context,
                    title: self.env._t("Open: ") + self.string,
                    viewId: view_id,
                    mode: !can_write || !write_access ? "readonly" : "edit",
                    onRecordSaved: () => self.props.value.model.load(),
                });
            }
        }
    },
});

Many2ManyTagsField.props = {
    ...Many2ManyTagsField.props,
    open: {type: Boolean, optional: true},
    canWrite: {type: Boolean, optional: true},
    nodeOptions: {type: Object, optional: true},
};

const Many2ManyTagsFieldExtractProps = Many2ManyTagsField.extractProps;
Many2ManyTagsField.extractProps = ({attrs, field}) => {
    const canOpen = Boolean(attrs.options.open);
    const canWrite = attrs.can_write && Boolean(JSON.parse(attrs.can_write));
    return Object.assign(Many2ManyTagsFieldExtractProps({attrs, field}), {
        open: canOpen,
        canWrite: canWrite,
        nodeOptions: attrs.options,
    });
};

/**
 *  Many2ManyTagsFieldColorEditable
 **/
patch(
    Many2ManyTagsFieldColorEditable.prototype,
    "web_m2x_options.Many2ManyTagsFieldColorEditable",
    {
        async onBadgeClick(event, record) {
            if (this.props.canEditColor && !this.props.open) {
                this._super(...arguments);
            }
            if (this.props.open) {
                Many2ManyTagsField.prototype.onMany2ManyBadgeClick.bind(this)(
                    event,
                    record
                );
            }
        },
    }
);

Many2ManyTagsFieldColorEditable.props = {
    ...Many2ManyTagsFieldColorEditable.props,
    open: {type: Boolean, optional: true},
    canWrite: {type: Boolean, optional: true},
    nodeOptions: {type: Object, optional: true},
};

/**
 *  CreateConfirmationDialog
 *  New customized component for Many2One Field
 **/

class CreateConfirmationDialog extends Component {
    get title() {
        return sprintf(this.env._t("New: %s"), this.props.name);
    }

    async onCreate() {
        await this.props.create();
        this.props.close();
    }
    async onCreateEdit() {
        await this.props.createEdit();
        this.props.close();
    }
}
CreateConfirmationDialog.components = {Dialog};
CreateConfirmationDialog.template =
    "web_m2x_options.Many2OneField.CreateConfirmationDialog";

/**
 *  Many2OneField
 **/

patch(Many2OneField.prototype, "web_m2x_options.Many2OneField", {
    setup() {
        this._super(...arguments);
        this.ir_options = Component.env.session.web_m2x_options;
    },
    /**
     * @override
     */
    get Many2XAutocompleteProps() {
        const props = this._super(...arguments);
        return {
            ...props,
            searchLimit: this.props.searchLimit,
            searchMore: this.props.searchMore,
            canCreate: this.props.canCreate,
            nodeOptions: this.props.nodeOptions,
        };
    },

    async openConfirmationDialog(request) {
        var m2o_dialog_opt =
            is_option_set(this.props.nodeOptions.m2o_dialog) ||
            (_.isUndefined(this.props.nodeOptions.m2o_dialog) &&
                is_option_set(this.ir_options["web_m2x_options.m2o_dialog"])) ||
            (_.isUndefined(this.props.nodeOptions.m2o_dialog) &&
                _.isUndefined(this.ir_options["web_m2x_options.m2o_dialog"]));
        if (this.props.canCreate && this.state.isFloating && m2o_dialog_opt) {
            return new Promise((resolve, reject) => {
                this.addDialog(CreateConfirmationDialog, {
                    value: request,
                    name: this.props.string,
                    create: async () => {
                        try {
                            await this.quickCreate(request);
                            resolve();
                        } catch (e) {
                            reject(e);
                        }
                    },
                    createEdit: async () => {
                        try {
                            await this.quickCreate(request);
                            await this.props.record.model.load();
                            this.openMany2X({
                                resId: this.props.value[0],
                                context: this.user_context,
                            });
                            resolve();
                        } catch (e) {
                            reject(e);
                        }
                    },
                });
            });
        }
    },
});

const Many2OneFieldExtractProps = Many2OneField.extractProps;
Many2OneField.extractProps = ({attrs, field}) => {
    return Object.assign(Many2OneFieldExtractProps({attrs, field}), {
        searchLimit: attrs.options.limit,
        searchMore: attrs.options.search_more,
        nodeOptions: attrs.options,
    });
};

Many2OneField.props = {
    ...Many2OneField.props,
    searchMore: {type: Boolean, optional: true},
    nodeOptions: {type: Object, optional: true},
};

/**
 * FIXME: find better way to extend props in Many2OneField
 * Override ReferenceField
 * Since extracted/added props: nodeOptions and searchMore into Many2OneField props
 * and this component inherited props from Many2OneField
 * So, must override props here to avoid constraint validateProps (props schema) in owl core
 */

ReferenceField.props = {
    ...ReferenceField.props,
    searchMore: {type: Boolean, optional: true},
    nodeOptions: {type: Object, optional: true},
};

/**
 * FIXME: find better way to extend props in Many2OneField
 * Override Many2OneBarcodeField
 * Since extracted/added props: nodeOptions and searchMore into Many2OneField props
 * and this component inherited props from Many2OneField
 * So, must override props here to avoid constraint validateProps (props schema) in owl core
 */

Many2OneBarcodeField.props = {
    ...Many2OneBarcodeField.props,
    searchMore: {type: Boolean, optional: true},
    nodeOptions: {type: Object, optional: true},
};

/**
 * FIXME: find better way to extend props in Many2OneField
 * Override Many2OneAvatarField
 * Since extracted/added props: nodeOptions and searchMore into Many2OneField props
 * and this component inherited props from Many2OneField
 * So, must override props here to avoid constraint validateProps (props schema) in owl core
 */
Many2OneAvatarField.props = {
    ...Many2OneAvatarField.props,
    searchMore: {type: Boolean, optional: true},
    nodeOptions: {type: Object, optional: true},
};

/**
 * FIXME: find better way to extend props in Many2OneField
 * Override mailing_m2o_filter
 * Since extracted/added props: nodeOptions and searchMore into Many2OneField props
 * and this component inherited props from Many2OneField
 * So, must override props here to avoid constraint validateProps (props schema) in owl core
 * This component is in module mass_mailing as optional module,
 * So need to import dynamic way
 */
try {
    (async () => {
        // Make sure component mailing_m2o_filter in mass mailing module loaded
        const installed_mass_mailing = await odoo.ready(
            "@mass_mailing/js/mailing_m2o_filter"
        );
        if (installed_mass_mailing) {
            const {FieldMany2OneMailingFilter} = await odoo.runtimeImport(
                "@mass_mailing/js/mailing_m2o_filter"
            );
            FieldMany2OneMailingFilter.props = {
                ...FieldMany2OneMailingFilter.props,
                searchMore: {type: Boolean, optional: true},
                nodeOptions: {type: Object, optional: true},
            };
        }
    })();
} catch {
    console.log(
        "Ignore overriding props of component mailing_m2o_filter since the module is not installed"
    );
}

/**
 *  X2ManyField
 **/
patch(X2ManyField.prototype, "web_m2x_options.X2ManyField", {
    /**
     * @override
     */
    async openRecord(record) {
        var self = this;
        var open = this.props.open;
        if (open && self.props.readonly) {
            var res_id = record.data.id;
            const action = await self.env.model.orm.call(
                self.props.value.resModel,
                "get_formview_action",
                [[res_id]]
            );
            return self.env.model.actionService.doAction(action);
        }
        return this._super.apply(this, arguments);
    },
});

const X2ManyFieldExtractProps = X2ManyField.extractProps;
X2ManyField.extractProps = ({attrs}) => {
    const canOpen = Boolean(attrs.options.open);
    return Object.assign(X2ManyFieldExtractProps({attrs}), {
        open: canOpen,
    });
};

X2ManyField.props = {
    ...X2ManyField.props,
    open: {type: Boolean, optional: true},
};

/**
 *  FormController
 **/
patch(FormController.prototype, "web_m2x_options.FormController", {
    /**
     * @override
     */
    setup() {
        var self = this;
        this._super(...arguments);

        /**  Due to problem of 2 onWillStart in native web core
         * (see: https://github.com/odoo/odoo/blob/16.0/addons/web/static/src/views/model.js#L142)
         * do the trick to override beforeLoadResolver here to customize viewLimit
         */
        this.superBeforeLoadResolver = this.beforeLoadResolver;
        this.beforeLoadResolver = async () => {
            await self._setSubViewLimit();
            self.superBeforeLoadResolver();
        };
    },
    /**
     * @override
     * add more method to add subview limit on formview
     */
    async _setSubViewLimit() {
        const ir_options = Component.env.session.web_m2x_options;

        const activeFields = this.archInfo.activeFields,
            fields = this.props.fields,
            isSmall = this.user;

        var limit = ir_options["web_m2x_options.field_limit_entries"];
        if (!_.isUndefined(limit)) {
            limit = parseInt(limit, 10);
        }

        for (const fieldName in activeFields) {
            const field = fields[fieldName];
            if (!isX2Many(field)) {
                // What follows only concerns x2many fields
                continue;
            }
            const fieldInfo = activeFields[fieldName];
            if (fieldInfo.modifiers.invisible === true) {
                // No need to fetch the sub view if the field is always invisible
                continue;
            }

            if (!fieldInfo.FieldComponent.useSubView) {
                // The FieldComponent used to render the field doesn't need a sub view
                continue;
            }

            let viewType = fieldInfo.viewMode || "list,kanban";
            viewType = viewType.replace("tree", "list");
            if (viewType.includes(",")) {
                viewType = isSmall ? "kanban" : "list";
            }
            fieldInfo.viewMode = viewType;
            if (fieldInfo.views[viewType] && limit) {
                fieldInfo.views[viewType].limit = limit;
            }
        }
    },
});
