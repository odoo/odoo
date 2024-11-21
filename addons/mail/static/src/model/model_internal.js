import { ATTR_SYM, MANY_SYM, ONE_SYM } from "./misc";

export class ModelInternal {
    /** @type {Map<string, boolean>} */
    fields = new Map();
    /** @type {Map<string, boolean>} */
    fieldsAttr = new Map();
    /** @type {Map<string, boolean>} */
    fieldsOne = new Map();
    /** @type {Map<string, boolean>} */
    fieldsMany = new Map();
    /** @type {Map<string, boolean>} */
    fieldsHtml = new Map();
    /** @type {Map<string, string>} */
    fieldsTargetModel = new Map();
    /** @type {Map<string, () => any>} */
    fieldsCompute = new Map();
    /** @type {Map<string, boolean>} */
    fieldsEager = new Map();
    /** @type {Map<string, string>} */
    fieldsInverse = new Map();
    /** @type {Map<string, () => void>} */
    fieldsOnAdd = new Map();
    /** @type {Map<string, () => void>} */
    fieldsOnDelete = new Map();
    /** @type {Map<string, () => void>} */
    fieldsOnUpdate = new Map();
    /** @type {Map<string, () => number>} */
    fieldsSort = new Map();
    /** @type {Map<string, string>} */
    fieldsType = new Map();

    prepareField(fieldName, data) {
        this.fields.set(fieldName, true);
        if (data[ATTR_SYM]) {
            this.fieldsAttr.set(fieldName, true);
        }
        if (data[ONE_SYM]) {
            this.fieldsOne.set(fieldName, true);
        }
        if (data[MANY_SYM]) {
            this.fieldsMany.set(fieldName, true);
        }
        for (const key in data) {
            const value = data[key];
            switch (key) {
                case "html": {
                    if (!value) {
                        break;
                    }
                    this.fieldsHtml.set(fieldName, value);
                    break;
                }
                case "targetModel": {
                    this.fieldsTargetModel.set(fieldName, value);
                    break;
                }
                case "compute": {
                    this.fieldsCompute.set(fieldName, value);
                    break;
                }
                case "eager": {
                    if (!value) {
                        break;
                    }
                    this.fieldsEager.set(fieldName, value);
                    break;
                }
                case "sort": {
                    this.fieldsSort.set(fieldName, value);
                    break;
                }
                case "inverse": {
                    this.fieldsInverse.set(fieldName, value);
                    break;
                }
                case "onAdd": {
                    this.fieldsOnAdd.set(fieldName, value);
                    break;
                }
                case "onDelete": {
                    this.fieldsOnDelete.set(fieldName, value);
                    break;
                }
                case "onUpdate": {
                    this.fieldsOnUpdate.set(fieldName, value);
                    break;
                }
                case "type": {
                    this.fieldsType.set(fieldName, value);
                    break;
                }
            }
        }
    }
}
