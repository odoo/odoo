
/** @odoo-module **/

import { _insertAction } from '@mail/core/model/_insert-action';
import { _insertField } from '@mail/core/model/_insert-field';
import { _insertIdentification } from '@mail/core/model/_insert-identification';
import { _insertModel } from '@mail/core/model/_insert-model';
import { _insertPrimitive } from '@mail/core/model/_insert-primitive';
import { _insertRecord } from '@mail/core/model/_insert-record';

export function _insert(ctx, data) {
    const data2 = { ...data };
    const type = data['Record/type'];
    delete data2['Record/type'];
    if (!type) {
        throw new Error(`No Record/type provided to stuff to insert.`);
    }
    let $;
    switch (type) {
        case 'Action': {
            $ = _insertAction(ctx, data2);
            break;
        }
        case 'Field': {
            $ = _insertField(ctx, data2);
            break;
        }
        case 'Identification': {
            $ = _insertIdentification(ctx, data2);
            break;
        }
        case 'Model': {
            $ = _insertModel(ctx, data2);
            break;
        }
        case 'Primitive': {
            $ = _insertPrimitive(ctx, data2);
            break;
        }
        case 'Record': {
            $ = _insertRecord(ctx, data2);
            break;
        }
        default: {
            debugger;
            throw new Error(`Unsupported Record/type "${type}" for insertion.`);
        }
    }
    return $;
}
