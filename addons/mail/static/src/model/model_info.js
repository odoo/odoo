/** @odoo-module **/

import { ModelIndexAnd } from '@mail/model/model_index_and';
import { ModelIndexXor } from '@mail/model/model_index_xor';

export class ModelInfo {

    constructor({ model, identifyingMode }) {
        this.model = model;
        this.identifyingMode = identifyingMode;
        this.records = new Set();
        this.recordCount = 0;
        this.recordsIndex = (() => {
            switch (this.identifyingMode) {
                case 'and':
                    return new ModelIndexAnd(model);
                case 'xor':
                    return new ModelIndexXor(model);
            }
        })();
        /**
         * Object with fieldName/field as key/value pair, for quick access.
         */
        this.fieldMap = new Map();
        this.combinedFields = {};
    }

}
