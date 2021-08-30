
/** @odoo-module **/

import { _insert } from '@mail/core/model/_insert';
import { _setup_01_Record } from '@mail/core/model/_setup-01-record';
import { _setup_02_Model } from '@mail/core/model/_setup-02-model';
import { _setup_03_Field } from '@mail/core/model/_setup-03-field';
import { _setup_04_Identification } from '@mail/core/model/_setup-04-identification';
import { ready } from '@mail/core/model/ready';

export function setup() {
    const ctx = 'setup';
    _setup_01_Record(ctx);
    _setup_02_Model(ctx);
    _setup_03_Field(ctx);
    _setup_04_Identification(ctx);

    // Record/insert
    _insert(null, {
        'Record/type': 'Action',
        'Action/name': 'Record/insert',
        'Action/behavior': (ctx, data) => _insert(ctx, data),
    });
    ready.resolve();
}
