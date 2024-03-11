/** @odoo-module **/

import {
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";

import { Many2OneAvatarEmployee } from '@hr/js/m2x_avatar_employee';
import { dom } from 'web.test_utils';

QUnit.module('hr', {}, function () {
    QUnit.module('M2XAvatarEmployeeLegacy', {
        beforeEach() {
            Many2OneAvatarEmployee.prototype.partnerIds = {};
        },
    });

    QUnit.test('many2one_avatar_employee: click on an employee not associated with a user', async function (assert) {
        assert.expect(6);

        const pyEnv = await startServer();
        const hrEmployeePublicId1 = pyEnv['hr.employee.public'].create({ name: 'Mario' });
        const m2xHrAvatarUserId1 = pyEnv['m2x.avatar.employee'].create({ employee_id: hrEmployeePublicId1 });
        const views = {
            'm2x.avatar.employee,false,form': '<form js_class="legacy_form"><field name="employee_id" widget="many2one_avatar_employee"/></form>',
        };
        const { openView } = await start({
            mockRPC(route, args) {
                if (args.method === 'read') {
                    assert.step(`read ${args.model} ${args.args[0]}`);
                }
            },
            serverData: { views },
            services: {
                notification: makeFakeNotificationService(message => {
                    assert.ok(
                        true,
                        "should display a toast notification after failing to open chat"
                    );
                    assert.strictEqual(
                        message,
                        "You can only chat with employees that have a dedicated user.",
                        "should display the correct information in the notification"
                    );
                }),
            },
        });

        await openView({
            res_model: 'm2x.avatar.employee',
            res_id: m2xHrAvatarUserId1,
            views: [[false, 'form']],
        });
        assert.strictEqual(document.querySelector('.o_field_widget[name=employee_id]').innerText.trim(), 'Mario');

        await dom.click(document.querySelector('.o_m2o_avatar > img'));

        assert.verifySteps([
            `read m2x.avatar.employee ${m2xHrAvatarUserId1}`,
            `read hr.employee.public ${hrEmployeePublicId1}`,
        ]);
    });

    QUnit.test('many2many_avatar_employee widget in form view', async function (assert) {
        assert.expect(8);

        const pyEnv = await startServer();
        const [resPartnerId1, resPartnerId2] = pyEnv['res.partner'].create([{}, {}]);
        const [resUsersId1, resUsersId2] = pyEnv['res.users'].create([{}, {}]);
        const [hrEmployeePublicId1, hrEmployeePublicId2] = pyEnv['hr.employee.public'].create([
            { user_id: resUsersId1, user_partner_id: resPartnerId1 },
            { user_id: resUsersId2, user_partner_id: resPartnerId2 },
        ]);
        const m2xAvatarEmployeeId1 = pyEnv['m2x.avatar.employee'].create(
            { employee_ids: [hrEmployeePublicId1, hrEmployeePublicId2] },
        );
        const views = {
            'm2x.avatar.employee,false,form': '<form js_class="legacy_form"><field name="employee_ids" widget="many2many_avatar_employee"/></form>',
        };
        const { openView } = await start({
            mockRPC(route, args) {
                if (args.method === 'read') {
                    assert.step(`read ${args.model} ${args.args[0]}`);
                }
            },
            serverData: { views },
        });

        await openView({
            res_model: 'm2x.avatar.employee',
            res_id: m2xAvatarEmployeeId1,
            views: [[false, 'form']],
        });
        assert.containsN(document.body, '.o_field_many2manytags.avatar.o_field_widget .badge', 2,
            "should have 2 records");
        assert.strictEqual(document.querySelector('.o_field_many2manytags.avatar.o_field_widget .badge img').getAttribute('data-src'),
            `/web/image/hr.employee.public/${hrEmployeePublicId1}/avatar_128`,
            "should have correct avatar image");

        await dom.click(document.querySelector('.o_field_many2manytags.avatar .badge .o_m2m_avatar'));
        await dom.click(document.querySelectorAll('.o_field_many2manytags.avatar .badge .o_m2m_avatar')[1]);

        assert.verifySteps([
            `read m2x.avatar.employee ${m2xAvatarEmployeeId1}`,
            `read hr.employee.public ${hrEmployeePublicId1},${hrEmployeePublicId2}`,
            `read hr.employee.public ${hrEmployeePublicId1}`,
            `read hr.employee.public ${hrEmployeePublicId2}`,
        ]);

        assert.containsN(
            document.body,
            '.o_ChatWindowHeader_name',
            2,
            "should have 2 chat windows"
        );
    });

    QUnit.test('many2many_avatar_employee: click on an employee not associated with a user', async function (assert) {
        assert.expect(10);

        const pyEnv = await startServer();
        const resPartnerId1 = pyEnv['res.partner'].create({});
        const resUsersId1 = pyEnv['res.users'].create({});
        const [hrEmployeePublicId1, hrEmployeePublicId2] = pyEnv['hr.employee.public'].create([
            {},
            { user_id: resUsersId1, user_partner_id: resPartnerId1 },
        ]);
        const m2xAvatarEmployeeId1 = pyEnv['m2x.avatar.employee'].create(
            { employee_ids: [hrEmployeePublicId1, hrEmployeePublicId2] },
        );
        const views = {
            'm2x.avatar.employee,false,form': '<form js_class="legacy_form"><field name="employee_ids" widget="many2many_avatar_employee"/></form>',
        };
        const { openView } = await start({
            mockRPC(route, args) {
                if (args.method === 'read') {
                    assert.step(`read ${args.model} ${args.args[0]}`);
                }
            },
            serverData: { views },
            services: {
                notification: makeFakeNotificationService(message => {
                    assert.ok(
                        true,
                        "should display a toast notification after failing to open chat"
                    );
                    assert.strictEqual(
                        message,
                        "You can only chat with employees that have a dedicated user.",
                        "should display the correct information in the notification"
                    );
                }),
            },
        });
        await openView({
            res_model: 'm2x.avatar.employee',
            res_id: m2xAvatarEmployeeId1,
            views: [[false, 'form']],
        });

        assert.containsN(document.body, '.o_field_many2manytags.avatar.o_field_widget .badge', 2,
            "should have 2 records");
        assert.strictEqual(document.querySelector('.o_field_many2manytags.avatar.o_field_widget .badge img').getAttribute('data-src'),
            `/web/image/hr.employee.public/${hrEmployeePublicId1}/avatar_128`,
            "should have correct avatar image");

        await dom.click(document.querySelector('.o_field_many2manytags.avatar .badge .o_m2m_avatar'));
        await dom.click(document.querySelectorAll('.o_field_many2manytags.avatar .badge .o_m2m_avatar')[1]);

        assert.verifySteps([
            `read m2x.avatar.employee ${hrEmployeePublicId1}`,
            `read hr.employee.public ${hrEmployeePublicId1},${hrEmployeePublicId2}`,
            `read hr.employee.public ${hrEmployeePublicId1}`,
            `read hr.employee.public ${hrEmployeePublicId2}`
        ]);

        assert.containsOnce(document.body, '.o_ChatWindowHeader_name',
            "should have 1 chat window");
    });
});
