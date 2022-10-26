/** @odoo-module **/

import { ModelIndexAnd } from '@mail/model/model_index_and';
import { ModelIndexXor } from '@mail/model/model_index_xor';

export class ModelInfo {

    constructor(manager, { model, identifyingMode }) {
        this.manager = manager;
        this.model = model;
        this.identifyingMode = identifyingMode;
        this.records = new Set();
        this.recordCount = 0;
        this.recordsIndex = (() => {
            switch (this.identifyingMode) {
                case 'and':
                    return new ModelIndexAnd(manager, model);
                case 'xor':
                    return new ModelIndexXor(manager, model);
            }
        })();
        /**
         * Object with fieldName/field as key/value pair, for quick access.
         */
        this.fieldMap = new Map();
        /**
         * List of all fields, for iterating.
         */
        this.fieldList = [];
        this.combinedFields = {};
        this.requiredFieldsList = [];
        this.identifyingFieldNames = new Set();
        this.fields = {};
    }

}
