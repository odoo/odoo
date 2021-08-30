/** @odoo-module **/

import { dispatch } from '@mail/core/model/dispatch';
import { ready } from '@mail/core/model/ready';

let $id = 0;

export async function Define(definition) {
    await ready;
    dispatch(null, 'Record/insert', {
        'Record/type': 'Record', // just for easy 1st impl.
        'Record/models': 'Definition',
        'Definition/id': $id,
        'Definition/raw': definition[0],
    });
    $id++;
}
