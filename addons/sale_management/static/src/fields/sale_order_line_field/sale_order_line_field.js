import { getSectionRecords } from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import {
    SaleOrderLineListRenderer,
    SaleOrderLineOne2Many,
} from "@sale/js/sale_order_line_field/sale_order_line_field";
import { makeContext } from "@web/core/context";
import { _t } from "@web/core/l10n/translation";
import { x2ManyCommands } from "@web/core/orm_service";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { uuid } from "@web/core/utils/strings";
import { getFieldsSpec } from "@web/model/relational_model/utils";
import { useSubEnv } from "@web/owl2/utils";

patch(SaleOrderLineOne2Many.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({ sectionTemplates: [] });

        useSubEnv({
            onSaveSectionTemplate: this.saveSectionTemplate.bind(this),
            onAddSectionTemplate: this.applySectionTemplate.bind(this),
            onDeleteSectionTemplate: this.deleteSectionTemplate.bind(this),
            canBeSavedAsTemplate: this.canBeSavedAsTemplate.bind(this),
            getSaveAsTemplateButtonTooltip: this.getSaveAsTemplateButtonTooltip.bind(this),
            state: this.state,
        });

        onWillStart(async () => {
            if (this.canCreate) {
                await this.loadSectionTemplates();
            }
        });

        onWillUpdateProps(async (nextProps) => {
            // reload section templates if the company has changed
            if (this.props.record.data.company_id.id !== nextProps.record.data.company_id.id) {
                await this.loadSectionTemplates(nextProps.record.data.company_id.id);
            }
        });
    },

    async loadSectionTemplates(companyId = this.props.record.data.company_id.id) {
        this.state.sectionTemplates = await this.orm.call(
            "sale.order.template",
            "get_section_templates",
            [companyId]
        );
    },

    /**
     * Apply a section template to the current sale order.
     *
     * Retrieves prepared sale.order.line values for the given section template,
     * assigns proper sequence values, and appends the resulting lines to the order.
     *
     * @param {number} templateId - resId of the section template to apply
     */
    async applySectionTemplate(templateId) {
        const fieldsSpec = getFieldsSpec(
            this.list.activeFields,
            this.list.fields,
            this.list.evalContext,
            { withInvisible: true }
        );
        const orderChanges = {
            order_id: {
                ...(await this.props.record.getChanges()),
                ...(!this.props.record.isNew && { id: this.props.record.resId }),
            },
        };

        const orderLineValues = await this.orm.call(
            "sale.order.template",
            "prepare_section_template_order_lines",
            [templateId, orderChanges, fieldsSpec]
        );

        // Start from 10 if there are no existing lines
        const maxSequence = Math.max(9, ...this.list.records.map((record) => record.data.sequence));
        const createCommands = orderLineValues.map((lineValues, index) =>
            x2ManyCommands.create(undefined, {
                ...lineValues,
                sequence: maxSequence + index + 1,
            })
        );

        await this.list.applyCommands(createCommands, { sort: true });
    },

    async deleteSectionTemplate(templateId) {
        await this.orm.call("sale.order.template", "unlink_section_template", [templateId]);
        await this.loadSectionTemplates();
    },

    /**
     * Saves a section template from section record.
     *
     * If the sale order is new or currently being edited,
     * it is first saved to the database to obtain a stable resId.
     *
     * @param {Object} record - section record to create template from.
     */
    async saveSectionTemplate(record) {
        if (!this.canBeSavedAsTemplate(record)) {
            return;
        }

        let sectionRecord = record;
        // If order is being created or has unsaved changes(dirty) we must save order first
        if (this.props.record.isNew || this.props.record.dirty) {
            // A virtual_id is assigned before saving so we can reliably retrieve
            // the record after the model reloads because at that point, the list is
            // entirely re-fetched and old record references are no longer valid.
            const virtualId = record.data.virtual_id || uuid();

            if (!record.data.virtual_id) {
                await record.update({ virtual_id: virtualId });
            }

            const saved = await this.props.record.save();
            if (!saved) {
                return;
            }
            // load list with new records
            await this.list.model.load();

            sectionRecord = this.list.records.find((r) => r.data.virtual_id === virtualId);
        }

        const result = await this.orm.call("sale.order.line", "save_section_template", [
            sectionRecord.resId,
        ]);

        const templateIndex = this.state.sectionTemplates.findIndex(
            (template) => template.id === result.id
        );

        // Add new template or update existing one if found in state
        let successMessage = "";
        if (templateIndex === -1) {
            this.state.sectionTemplates.push(result);
            successMessage = _t("Section template %s created successfully", result.name);
        } else {
            this.state.sectionTemplates[templateIndex] = result;
            successMessage = _t("Section template %s updated successfully", result.name);
        }

        this.notificationService.add(successMessage, { type: "success" });
    },

    canBeSavedAsTemplate(sectionRecord) {
        return !this.sectionHasCombos(sectionRecord);
    },

    sectionHasCombos(record) {
        const sectionRecords = getSectionRecords(this.list, record);
        return sectionRecords.some(
            (sectionRecord) =>
                sectionRecord.data.product_type === "combo" || sectionRecord.data.combo_item_id
        );
    },

    getSaveAsTemplateButtonTooltip(record) {
        return this.sectionHasCombos(record)
            ? _t("You cannot save a section with combo lines as a template")
            : "";
    },
});

patch(SaleOrderLineListRenderer, {
    rowsTemplate: "sale_management.ListRenderer.Rows",
});

patch(SaleOrderLineListRenderer.prototype, {
    setup() {
        super.setup();
        this.copyFields.push('is_optional');
        this.user = user;
    },

    /**
     * Disable "Hide Composition" and "Hide Prices" buttons for optional sections and their
     * subsections.
     */
    disableCompositionButton(record) {
        return (
            super.disableCompositionButton(record) ||
            this.shouldCollapse(record, 'is_optional', true)
        );
    },

    disablePricesButton(record) {
        return (
            super.disablePricesButton(record) || this.shouldCollapse(record, 'is_optional', true)
        );
    },

    /**
     * Disable "Set Optional" button if
     *  - Parent section is optional
     *  - Parent section hides prices or composition
     *  - Section itself hides prices or composition
     */
    disableOptionalButton(record) {
        return (
            this.shouldCollapse(record, 'is_optional')
            || this.shouldCollapse(record, 'collapse_prices', true)
            || this.shouldCollapse(record, 'collapse_composition', true)
        );
    },

    get isCurrentSectionOptional() {
        if (this.props.list.records.length === 0) return false;

        return this.shouldCollapse(
            this.props.list.records[this.props.list.records.length - 1],
            'is_optional',
            true
        );
    },

    /**
     * Override to set the default `product_uom_qty` to 0 for new lines created under an optional
     * section.
     */
    add(params){
        params.context = this.getCreateContext(params);
        super.add(params);
    },

    getCreateContext(params) {
        const evaluatedContext = makeContext([params.context]);
        // A falsy context indicates a product line (no `display_type` specified)
        if (!evaluatedContext[`default_display_type`] && this.isCurrentSectionOptional) {
            return { ...evaluatedContext, default_product_uom_qty: 0 };
        }
        return params.context;
    },

    /**
     * Override to set the default `product_uom_qty` to 0 for new lines inserted by optional
     * sections from dropdown.
     */
    getInsertLineContext(record, addSubSection) {
        if (this.shouldCollapse(record, 'is_optional', true) && !addSubSection) {
            return {
                ...super.getInsertLineContext(record, addSubSection),
                default_product_uom_qty: 0
            };
        }
        return super.getInsertLineContext(record, addSubSection);
    },

    getRowClass(record) {
        let rowClasses = super.getRowClass(record);
        if (this.shouldCollapse(record, 'is_optional')) {
            rowClasses += ' text-primary';
        }
        return rowClasses;
    },

    /**
     * @override
     * This override resets optional state of subsections when their parent sections is collapsed
     */
    async toggleCollapse(record, fieldName) {
        await super.toggleCollapse(record, fieldName);

        if (this.isTopSection(record) && record.data[fieldName]) {
            const commands = [];

            for (const sectionRecord of getSectionRecords(this.props.list, record)) {
                if (this.isSubSection(sectionRecord)) {
                    commands.push(
                        x2ManyCommands.update(sectionRecord.resId || sectionRecord._virtualId, {
                            is_optional: false,
                        })
                    )
                }
            }

            if (commands.length) {
                await this.props.list.applyCommands(commands, { sort: true });
            }
        }
    },

    /**
     * Toggles optional state on a section:
     * - Product lines → qty = 0 when set optional, reset to 1 when unset.
     * - Subsections → force hide composition/prices to false.
     */
    async toggleIsOptional(record) {
        const setOptional = !record.data.is_optional;

        const commands = [(x2ManyCommands.update(record.resId || record._virtualId, {
            is_optional: setOptional,
        }))];

        const proms = [];
        for (const sectionRecord of getSectionRecords(this.props.list, record)) {
            let changes = {};

            if (!sectionRecord.data.display_type) {
                if (setOptional) {
                    changes = { product_uom_qty: 0, price_total: 0, price_subtotal: 0 }
                } else {
                    proms.push(sectionRecord._update({ product_uom_qty: sectionRecord.data.product_uom_qty || 1 }));
                }
            } else if (this.isSubSection(sectionRecord)) {
                changes = setOptional && {
                    collapse_composition: false,
                    collapse_prices: false,
                };
            }

            if (Object.keys(changes).length) {
                commands.push(
                    x2ManyCommands.update(
                        sectionRecord.resId || sectionRecord._virtualId,
                        changes
                    )
                );
            }
        }

        await this.props.list.applyCommands(commands, { sort: true });
        await Promise.all(proms);
    },

    /**
     * @override
     * Handles product line quantity adjustments when a record is dragged and dropped.
     *
     * Behavior:
     * - If a product line is moved under an optional section, its quantity is set to `0`.
     * - If a product line is dragged out of an optional section and had `0` quantity,
     *   its quantity is reset to `1`.
     * - Non-product lines (`display_type` set) are ignored.
     */
    async sortDrop(dataRowId, dataGroupId, { element, previous }) {
        const record = this.props.list.records.find(r => r.id === dataRowId);
        // Prevent the record from being abandoned when leaveEditMode or sortDrop is called
        record.dirty = true;
        await this.props.list.leaveEditMode();
        const recordMap = this._getRecordsToRecompute(record, previous ? previous.dataset.id : null);

        await super.sortDrop(dataRowId, dataGroupId, { element, previous });

        await this._handleQuantityAdjustment(recordMap);
    },

    /**
     * Builds a map of records whose optional state needs to be recomputed
     * after a record is moved within the list.
     *
     * The map’s keys are record IDs, and values represent their current
     * `is_optional` collapse state as determined by `shouldCollapse()`.
     *
     * @param {Object} record - The record being moved.
     * @param {number|string} targetId - The ID of the record that serves as the new drop target.
     * @returns {Map<number|string, boolean>} A map of record IDs to their recomputed optional states.
     */
    _getRecordsToRecompute(record, targetId) {
        const optionalStateMap = new Map();

        if (this.isSection(record)) { // If a section or subsection is moved
            let currentIndex = this.props.list.records.indexOf(record);
            let targetIndex = this.props.list.records.findIndex(r => r.id === targetId);
            if (currentIndex > targetIndex) {
                //When moving up, recompute:
                // 1. All records under the moved section.
                // 2. All records between the new and old positions.
                for (let i = currentIndex; i > targetIndex; i--) {
                    if (!this.props.list.records[i].data.display_type) {
                        optionalStateMap.set(
                            this.props.list.records[i].id,
                            this.shouldCollapse(this.props.list.records[i], 'is_optional')
                        );
                    }
                }
                for (const sectionRecord of getSectionRecords(this.props.list, record)) {
                    if (!sectionRecord.data.display_type) {
                        optionalStateMap.set(sectionRecord.id, this.shouldCollapse(sectionRecord, 'is_optional'));
                    }
                }
            } else {
                //When moving down, recompute:
                // 1. All records under sections between the old and new positions.
                // 2. All records between the old and new positions (skipping overlaps).
                for (let i = currentIndex; i <= targetIndex; i++) {
                    if (this.isSection(this.props.list.records[i])) {
                        for (const sectionRecord of getSectionRecords(this.props.list, this.props.list.records[i])) {
                            if (
                                !optionalStateMap.has(sectionRecord.id)
                                && !sectionRecord.data.display_type
                            ) {
                                optionalStateMap.set(
                                    sectionRecord.id,
                                    this.shouldCollapse(sectionRecord, 'is_optional')
                                );
                            }
                        }
                    }

                    // we must skip overlapping records
                    if (
                        !optionalStateMap.has(this.props.list.records[i].id)
                        && !this.props.list.records[i].data.display_type
                    ) {
                        optionalStateMap.set(
                            this.props.list.records[i].id,
                            this.shouldCollapse(this.props.list.records[i], 'is_optional')
                        );
                    }
                }
            }
        } else if (!record.data.display_type) { // If a regular record is moved compute its own optional state
            optionalStateMap.set(record.id, this.shouldCollapse(record, 'is_optional'));
        }

        return optionalStateMap;
    },

    async _handleQuantityAdjustment(recordMap) {
        const commands = [];

        for (const [recordId, wasOptional] of recordMap.entries()) {
            const record = this.props.list.records.find(r => r.id === recordId);
            const isOptional = this.shouldCollapse(record, 'is_optional');

            if (wasOptional && !isOptional && !record.data.product_uom_qty) {
                commands.push(x2ManyCommands.update(
                    record.resId || record._virtualId, { product_uom_qty: 1 }
                ));
            } else if (!wasOptional && isOptional) {
                commands.push(x2ManyCommands.update(
                    record.resId || record._virtualId, { product_uom_qty: 0 }
                ));
            }
        }

        await this.props.list.applyCommands(commands, { sort: true });
    },

    /**
     * @override
     * Reset fields when a subsection is moved under an optional section,
     * since optional sections cannot contain hidden subsections or hidden prices.
     */
    resetOnResequence(record, parentSection) {
        return (
            super.resetOnResequence(record, parentSection)
            || (
                this.isSubSection(record)
                && (
                    parentSection?.data.is_optional
                    || parentSection?.data.collapse_composition
                ) && (
                    record.data.collapse_composition
                    || record.data.collapse_prices
                    || record.data.is_optional
                )
            )
        );
    },

    fieldsToReset() {
        return { ...super.fieldsToReset(), is_optional: false };
    },

    async moveCombo(record, direction) {
        const wasOptional = this.shouldCollapse(record, 'is_optional');

        await super.moveCombo(record, direction);

        const isOptional = this.shouldCollapse(record, 'is_optional');

        if (wasOptional && !isOptional && !record.data.product_uom_qty) {
            await record.update({ product_uom_qty: 1 });
        } else if (!wasOptional && isOptional) {
            await record.update({ product_uom_qty: 0 });
        }
    },
});
