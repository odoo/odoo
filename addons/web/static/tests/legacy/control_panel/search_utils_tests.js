odoo.define('web.search_utils_tests', function (require) {
    "use strict";

    const { constructDateDomain } = require('web.searchUtils');
    const testUtils = require('web.test_utils');
    const { _t } = require('web.core');

    const patchDate = testUtils.mock.patchDate;

    QUnit.module('SearchUtils', function () {

        QUnit.module('Construct domain');

        QUnit.test('construct simple domain based on date field (no comparisonOptionId)', function (assert) {
            assert.expect(4);
            const unpatchDate = patchDate(2020, 5, 1, 13, 0, 0);
            const referenceMoment = moment().utc();
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', []),
                {
                    domain: "[]",
                    description: "",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', ['this_month', 'this_year']),
                {
                    domain: `["&", ["date_field", ">=", "2020-06-01"], ["date_field", "<=", "2020-06-30"]]`,
                    description: "June 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', ['second_quarter', 'this_year']),
                {
                    domain: `["&", ["date_field", ">=", "2020-04-01"], ["date_field", "<=", "2020-06-30"]]`,
                    description: "Q2 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', ['this_year']),
                {
                    domain: `["&", ["date_field", ">=", "2020-01-01"], ["date_field", "<=", "2020-12-31"]]`,
                    description: "2020",
                }
            );
            unpatchDate();
        });

        QUnit.test('construct simple domain based on datetime field (no comparisonOptionId)', function (assert) {
            assert.expect(3);
            const unpatchDate = patchDate(2020, 5, 1, 13, 0, 0);
            const referenceMoment = moment().utc();
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'datetime', ['this_month', 'this_year']),
                {
                    domain: `["&", ["date_field", ">=", "2020-06-01 00:00:00"], ["date_field", "<=", "2020-06-30 23:59:59"]]`,
                    description: "June 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'datetime', ['second_quarter', 'this_year']),
                {
                    domain: `["&", ["date_field", ">=", "2020-04-01 00:00:00"], ["date_field", "<=", "2020-06-30 23:59:59"]]`,
                    description: "Q2 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'datetime', ['this_year']),
                {
                    domain: `["&", ["date_field", ">=", "2020-01-01 00:00:00"], ["date_field", "<=", "2020-12-31 23:59:59"]]`,
                    description: "2020",
                }
            );
            unpatchDate();
        });

        QUnit.test('construct domain based on date field (no comparisonOptionId)', function (assert) {
            assert.expect(3);
            const unpatchDate = patchDate(2020, 0, 1, 12, 0, 0);
            const referenceMoment = moment().utc();
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', ['this_month', 'first_quarter', 'this_year']),
                {
                    domain: "[" +
                                `"|", ` +
                                    `"&", ["date_field", ">=", "2020-01-01"], ["date_field", "<=", "2020-01-31"], ` +
                                    `"&", ["date_field", ">=", "2020-01-01"], ["date_field", "<=", "2020-03-31"]` +
                            "]",
                    description: "January 2020/Q1 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', ['second_quarter', 'this_year', 'last_year']),
                {
                    domain: "[" +
                                `"|", ` +
                                    `"&", ["date_field", ">=", "2019-04-01"], ["date_field", "<=", "2019-06-30"], ` +
                                    `"&", ["date_field", ">=", "2020-04-01"], ["date_field", "<=", "2020-06-30"]` +
                            "]",
                    description: "Q2 2019/Q2 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', ['this_year', 'this_month', 'antepenultimate_month']),
                {
                    domain: "[" +
                                `"|", ` +
                                    `"&", ["date_field", ">=", "2020-01-01"], ["date_field", "<=", "2020-01-31"], ` +
                                    `"&", ["date_field", ">=", "2020-11-01"], ["date_field", "<=", "2020-11-30"]` +
                            "]",
                    description: "January 2020/November 2020",
                }
            );
            unpatchDate();
        });

        QUnit.test('construct domain based on datetime field (no comparisonOptionId)', function (assert) {
            assert.expect(3);
            const unpatchDate = patchDate(2020, 0, 1, 12, 0, 0);
            const referenceMoment = moment().utc();
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'datetime', ['this_month', 'first_quarter', 'this_year']),
                {
                    domain: "[" +
                                `"|", ` +
                                    `"&", ["date_field", ">=", "2020-01-01 00:00:00"], ["date_field", "<=", "2020-01-31 23:59:59"], ` +
                                    `"&", ["date_field", ">=", "2020-01-01 00:00:00"], ["date_field", "<=", "2020-03-31 23:59:59"]` +
                            "]",
                    description: "January 2020/Q1 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'datetime', ['second_quarter', 'this_year', 'last_year']),
                {
                    domain: "[" +
                                `"|", ` +
                                    `"&", ["date_field", ">=", "2019-04-01 00:00:00"], ["date_field", "<=", "2019-06-30 23:59:59"], ` +
                                    `"&", ["date_field", ">=", "2020-04-01 00:00:00"], ["date_field", "<=", "2020-06-30 23:59:59"]` +
                            "]",
                    description: "Q2 2019/Q2 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'datetime', ['this_year', 'this_month', 'antepenultimate_month']),
                {
                    domain: "[" +
                                `"|", ` +
                                    `"&", ["date_field", ">=", "2020-01-01 00:00:00"], ["date_field", "<=", "2020-01-31 23:59:59"], ` +
                                    `"&", ["date_field", ">=", "2020-11-01 00:00:00"], ["date_field", "<=", "2020-11-30 23:59:59"]` +
                            "]",
                    description: "January 2020/November 2020",
                }
            );
            unpatchDate();
        });

        QUnit.test('construct comparison domain based on date field and option "previous_period"', function (assert) {
            assert.expect(5);
            const unpatchDate = patchDate(2020, 0, 1, 12, 0, 0);
            const referenceMoment = moment().utc();
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', ['this_month', 'first_quarter', 'this_year'], 'previous_period'),
                {
                    domain: "[" +
                                `"|", "|", ` +
                                `"&", ["date_field", ">=", "2019-10-01"], ["date_field", "<=", "2019-10-31"], ` +
                                `"&", ["date_field", ">=", "2019-11-01"], ["date_field", "<=", "2019-11-30"], ` +
                                `"&", ["date_field", ">=", "2019-12-01"], ["date_field", "<=", "2019-12-31"]` +
                            "]",
                    description: "October 2019/November 2019/December 2019",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', ['second_quarter', 'this_year', 'last_year'], 'previous_period'),
                {
                    domain: "[" +
                                `"|", ` +
                                `"&", ["date_field", ">=", "2018-01-01"], ["date_field", "<=", "2018-03-31"], ` +
                                    `"&", ["date_field", ">=", "2019-01-01"], ["date_field", "<=", "2019-03-31"]` +
                            "]",
                    description: "Q1 2018/Q1 2019",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', ['this_year', 'antepenultimate_year', 'this_month', 'antepenultimate_month'], 'previous_period'),
                {
                    domain: "[" +
                                `"|", "|", "|", ` +
                                    `"&", ["date_field", ">=", "2015-02-01"], ["date_field", "<=", "2015-02-28"], ` +
                                    `"&", ["date_field", ">=", "2015-12-01"], ["date_field", "<=", "2015-12-31"], ` +
                                    `"&", ["date_field", ">=", "2017-02-01"], ["date_field", "<=", "2017-02-28"], ` +
                                    `"&", ["date_field", ">=", "2017-12-01"], ["date_field", "<=", "2017-12-31"]` +
                            "]",
                    description: "February 2015/December 2015/February 2017/December 2017",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', ['this_year', 'last_year'], 'previous_period'),
                {
                    domain: "[" +
                                `"|", ` +
                                    `"&", ["date_field", ">=", "2017-01-01"], ["date_field", "<=", "2017-12-31"], ` +
                                    `"&", ["date_field", ">=", "2018-01-01"], ["date_field", "<=", "2018-12-31"]` +
                            "]",
                    description: "2017/2018",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', ['second_quarter', 'third_quarter', 'last_year'], 'previous_period'),
                {
                    domain: "[" +
                                `"|", ` +
                                `"&", ["date_field", ">=", "2018-10-01"], ["date_field", "<=", "2018-12-31"], ` +
                                    `"&", ["date_field", ">=", "2019-01-01"], ["date_field", "<=", "2019-03-31"]` +
                            "]",
                    description: "Q4 2018/Q1 2019",
                }
            );
            unpatchDate();
        });

        QUnit.test('construct comparison domain based on datetime field and option "previous_year"', function (assert) {
            assert.expect(3);
            const unpatchDate = patchDate(2020, 5, 1, 13, 0, 0);
            const referenceMoment = moment().utc();
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'datetime', ['this_month', 'first_quarter', 'this_year'], 'previous_year'),
                {
                    domain: "[" +
                                `"|", ` +
                                    `"&", ["date_field", ">=", "2019-06-01 00:00:00"], ["date_field", "<=", "2019-06-30 23:59:59"], ` +
                                    `"&", ["date_field", ">=", "2019-01-01 00:00:00"], ["date_field", "<=", "2019-03-31 23:59:59"]` +
                            "]",
                    description: "June 2019/Q1 2019",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'datetime', ['second_quarter', 'this_year', 'last_year'], 'previous_year'),
                {
                    domain: "[" +
                                `"|", ` +
                                    `"&", ["date_field", ">=", "2018-04-01 00:00:00"], ["date_field", "<=", "2018-06-30 23:59:59"], ` +
                                    `"&", ["date_field", ">=", "2019-04-01 00:00:00"], ["date_field", "<=", "2019-06-30 23:59:59"]` +
                            "]",
                    description: "Q2 2018/Q2 2019",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'datetime', ['this_year', 'antepenultimate_year', 'this_month', 'antepenultimate_month'], 'previous_year'),
                {
                    domain: "[" +
                                `"|", "|", "|", ` +
                                `"&", ["date_field", ">=", "2017-04-01 00:00:00"], ["date_field", "<=", "2017-04-30 23:59:59"], ` +
                                `"&", ["date_field", ">=", "2017-06-01 00:00:00"], ["date_field", "<=", "2017-06-30 23:59:59"], ` +
                                `"&", ["date_field", ">=", "2019-04-01 00:00:00"], ["date_field", "<=", "2019-04-30 23:59:59"], ` +
                                `"&", ["date_field", ">=", "2019-06-01 00:00:00"], ["date_field", "<=", "2019-06-30 23:59:59"]` +
                            "]",
                    description: "April 2017/June 2017/April 2019/June 2019",
                }
            );
            unpatchDate();
        });

        QUnit.module('Options translation');

        QUnit.test("Quarter option: custom translation", async function (assert) {
            assert.expect(1);

            const unpatchDate = patchDate(2020, 5, 1, 13, 0, 0);
            const referenceMoment = moment().locale('en');
            testUtils.mock.patch(_t.database.db, {
                "Q2": "Deuxième trimestre de l'an de grâce",
            });

            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', ['second_quarter', 'this_year']),
                {
                    domain: `["&", ["date_field", ">=", "2020-04-01"], ["date_field", "<=", "2020-06-30"]]`,
                    description: "Deuxième trimestre de l'an de grâce 2020",
                },
                "Quarter term should be translated"
            );

            unpatchDate();
            testUtils.mock.unpatch(_t.database.db);
        });

        QUnit.test("Quarter option: right to left", async function (assert) {
            assert.expect(1);

            const unpatchDate = patchDate(2020, 5, 1, 13, 0, 0);
            const referenceMoment = moment().locale('en');
            testUtils.mock.patch(_t.database.parameters, {
                direction: "rtl",
            });

            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', ['second_quarter', 'this_year']),
                {
                    domain: `["&", ["date_field", ">=", "2020-04-01"], ["date_field", "<=", "2020-06-30"]]`,
                    description: "2020 Q2",
                },
                "Notation should be right to left"
            );

            unpatchDate();
            testUtils.mock.unpatch(_t.database.parameters);
        });

        QUnit.test("Quarter option: custom translation and right to left", async function (assert) {
            assert.expect(1);

            const unpatchDate = patchDate(2020, 5, 1, 13, 0, 0);
            const referenceMoment = moment().locale('en');
            testUtils.mock.patch(_t.database.db, {
                "Q2": "2e Trimestre",
            });
            testUtils.mock.patch(_t.database.parameters, {
                direction: "rtl",
            });

            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', ['second_quarter', 'this_year']),
                {
                    domain: `["&", ["date_field", ">=", "2020-04-01"], ["date_field", "<=", "2020-06-30"]]`,
                    description: "2020 2e Trimestre",
                },
                "Quarter term should be translated and notation should be right to left"
            );

            unpatchDate();
            testUtils.mock.unpatch(_t.database.db);
            testUtils.mock.unpatch(_t.database.parameters);
        });

        QUnit.test("Moment.js localization does not affect formatted domain dates", async function (assert) {
            assert.expect(1);

            const unpatchDate = patchDate(2020, 5, 1, 13, 0, 0);
            const initialLocale = moment.locale();
            moment.defineLocale('addoneForTest', {
                postformat: function (string) {
                    return string.replace(/\d/g, match => (1 + parseInt(match)) % 10);
                }
            });
            const referenceMoment = moment().locale('addoneForTest');

            assert.deepEqual(
                constructDateDomain(referenceMoment, 'date_field', 'date', ['this_month', 'this_year']),
                {
                    domain: `["&", ["date_field", ">=", "2020-06-01"], ["date_field", "<=", "2020-06-30"]]`,
                    description: "June 3131",
                },
                "Numbers in domain should not use addoneForTest locale"
            );

            moment.locale(initialLocale);
            moment.updateLocale("addoneForTest", null);
            unpatchDate();
        });
    });
});
