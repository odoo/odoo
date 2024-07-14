/** @odoo-module **/

import { session } from "@web/session";
import { accountMethodsForMobile } from "@web_mobile/js/core/mixins";
import mobile from '@web_mobile/js/services/core';
import { patchWithCleanup, clickSave, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";


const MY_IMAGE = 'iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==';
const BASE64_PNG_HEADER = "iVBORw0KGg";

let serverData;
let target;

QUnit.module("hr_mobile", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        serverData = {
            models: {
                users: {
                    fields: {
                        name: { string: "name", type: "char" },
                    },
                    records: [],
                },
            },
        };
        setupViewRegistries();
    });

    QUnit.test('EmployeeProfileFormView should call native updateAccount method when saving record', async function (assert) {
        assert.expect(4);

        patchWithCleanup(mobile.methods, {
            updateAccount( options ) {
                const { avatar, name, username } = options;
                assert.ok("should call updateAccount");
                assert.ok(avatar.startsWith(BASE64_PNG_HEADER), "should have a PNG base64 encoded avatar");
                assert.strictEqual(name, "Marc Demo");
                assert.strictEqual(username, "demo");
                return Promise.resolve();
            },
        });

        patchWithCleanup(session, {
            username: "demo",
            name: "Marc Demo",
        });

        patchWithCleanup(accountMethodsForMobile, {
            async fetchAvatar() {
                return `data:image/png;base64,${MY_IMAGE}`;
            },
        });

        await makeView({
            type: "form",
            resModel: 'users',
            serverData: serverData,
            arch: `
                <form js_class="hr_employee_profile_form">
                    <sheet>
                        <field name="name"/>
                    </sheet>
                </form>`,
        });

        await clickSave(target);
    });
});
