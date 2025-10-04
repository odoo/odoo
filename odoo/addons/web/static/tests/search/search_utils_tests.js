/** @odoo-module **/

import { defaultLocalization } from "@web/../tests/helpers/mock_services";
import { patchDate, patchTimeZone, patchWithCleanup } from "@web/../tests/helpers/utils";
import { Domain } from "@web/core/domain";
import { localization } from "@web/core/l10n/localization";
import { translatedTerms } from "@web/core/l10n/translation";
import { constructDateDomain } from "@web/search/utils/dates";

const { DateTime } = luxon;

QUnit.module("Search", () => {
    QUnit.module("SearchUtils", {
        beforeEach() {
            patchTimeZone(0);
        },
    });

    QUnit.test(
        "construct simple domain based on date field (no comparisonOptionId)",
        function (assert) {
            patchDate(2020, 5, 1, 13, 0, 0);
            const referenceMoment = DateTime.local();
            assert.deepEqual(constructDateDomain(referenceMoment, "date_field", "date", []), {
                domain: new Domain(`[]`),
                description: "",
            });
            assert.deepEqual(
                constructDateDomain(referenceMoment, "date_field", "date", [
                    "this_month",
                    "this_year",
                ]),
                {
                    domain: new Domain(
                        `["&", ("date_field", ">=", "2020-06-01"), ("date_field", "<=", "2020-06-30")]`
                    ),
                    description: "June 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, "date_field", "date", [
                    "second_quarter",
                    "this_year",
                ]),
                {
                    domain: new Domain(
                        `["&", ("date_field", ">=", "2020-04-01"), ("date_field", "<=", "2020-06-30")]`
                    ),
                    description: "Q2 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, "date_field", "date", ["this_year"]),
                {
                    domain: new Domain(
                        `["&", ("date_field", ">=", "2020-01-01"), ("date_field", "<=", "2020-12-31")]`
                    ),
                    description: "2020",
                }
            );
        }
    );

    QUnit.test(
        "construct simple domain based on date field (no comparisonOptionId) - UTC+2",
        (assert) => {
            patchTimeZone(120);
            patchDate(2020, 5, 1, 0, 0, 0);
            const referenceMoment = DateTime.local();
            assert.deepEqual(constructDateDomain(referenceMoment, "date_field", "date", []), {
                domain: new Domain(`[]`),
                description: "",
            });
            assert.deepEqual(
                constructDateDomain(referenceMoment, "date_field", "date", [
                    "this_month",
                    "this_year",
                ]),
                {
                    domain: new Domain(
                        `["&", ("date_field", ">=", "2020-06-01"), ("date_field", "<=", "2020-06-30")]`
                    ),
                    description: "June 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, "date_field", "date", [
                    "second_quarter",
                    "this_year",
                ]),
                {
                    domain: new Domain(
                        `["&", ("date_field", ">=", "2020-04-01"), ("date_field", "<=", "2020-06-30")]`
                    ),
                    description: "Q2 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, "date_field", "date", ["this_year"]),
                {
                    domain: new Domain(
                        `["&", ("date_field", ">=", "2020-01-01"), ("date_field", "<=", "2020-12-31")]`
                    ),
                    description: "2020",
                }
            );
        }
    );

    QUnit.test(
        "construct simple domain based on datetime field (no comparisonOptionId)",
        function (assert) {
            patchDate(2020, 5, 1, 13, 0, 0);
            const referenceMoment = DateTime.local();
            assert.deepEqual(
                constructDateDomain(referenceMoment, "date_field", "datetime", [
                    "this_month",
                    "this_year",
                ]),
                {
                    domain: new Domain(
                        `["&", ("date_field", ">=", "2020-06-01 00:00:00"), ("date_field", "<=", "2020-06-30 23:59:59")]`
                    ),
                    description: "June 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, "date_field", "datetime", [
                    "second_quarter",
                    "this_year",
                ]),
                {
                    domain: new Domain(
                        `["&", ("date_field", ">=", "2020-04-01 00:00:00"), ("date_field", "<=", "2020-06-30 23:59:59")]`
                    ),
                    description: "Q2 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, "date_field", "datetime", ["this_year"]),
                {
                    domain: new Domain(
                        `["&", ("date_field", ">=", "2020-01-01 00:00:00"), ("date_field", "<=", "2020-12-31 23:59:59")]`
                    ),
                    description: "2020",
                }
            );
        }
    );

    QUnit.test(
        "construct simple domain based on datetime field (no comparisonOptionId) - UTC+2",
        (assert) => {
            patchTimeZone(120);
            patchDate(2020, 5, 1, 0, 0, 0);
            const referenceMoment = DateTime.local();
            assert.deepEqual(
                constructDateDomain(referenceMoment, "date_field", "datetime", [
                    "this_month",
                    "this_year",
                ]),
                {
                    domain: new Domain(
                        `["&", ("date_field", ">=", "2020-05-31 22:00:00"), ("date_field", "<=", "2020-06-30 21:59:59")]`
                    ),
                    description: "June 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, "date_field", "datetime", [
                    "second_quarter",
                    "this_year",
                ]),
                {
                    domain: new Domain(
                        `["&", ("date_field", ">=", "2020-03-31 22:00:00"), ("date_field", "<=", "2020-06-30 21:59:59")]`
                    ),
                    description: "Q2 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, "date_field", "datetime", ["this_year"]),
                {
                    domain: new Domain(
                        `["&", ("date_field", ">=", "2019-12-31 22:00:00"), ("date_field", "<=", "2020-12-31 21:59:59")]`
                    ),
                    description: "2020",
                }
            );
        }
    );

    QUnit.test("construct domain based on date field (no comparisonOptionId)", function (assert) {
        patchDate(2020, 0, 1, 12, 0, 0);
        const referenceMoment = DateTime.local();
        assert.deepEqual(
            constructDateDomain(referenceMoment, "date_field", "date", [
                "this_month",
                "first_quarter",
                "this_year",
            ]),
            {
                domain: new Domain(
                    "[" +
                        `"|", ` +
                        `"&", ("date_field", ">=", "2020-01-01"), ("date_field", "<=", "2020-01-31"), ` +
                        `"&", ("date_field", ">=", "2020-01-01"), ("date_field", "<=", "2020-03-31")` +
                        "]"
                ),
                description: "January 2020/Q1 2020",
            }
        );
        assert.deepEqual(
            constructDateDomain(referenceMoment, "date_field", "date", [
                "second_quarter",
                "this_year",
                "last_year",
            ]),
            {
                domain: new Domain(
                    "[" +
                        `"|", ` +
                        `"&", ("date_field", ">=", "2019-04-01"), ("date_field", "<=", "2019-06-30"), ` +
                        `"&", ("date_field", ">=", "2020-04-01"), ("date_field", "<=", "2020-06-30")` +
                        "]"
                ),
                description: "Q2 2019/Q2 2020",
            }
        );
        assert.deepEqual(
            constructDateDomain(referenceMoment, "date_field", "date", [
                "this_year",
                "this_month",
                "antepenultimate_month",
            ]),
            {
                domain: new Domain(
                    "[" +
                        `"|", ` +
                        `"&", ("date_field", ">=", "2020-01-01"), ("date_field", "<=", "2020-01-31"), ` +
                        `"&", ("date_field", ">=", "2020-11-01"), ("date_field", "<=", "2020-11-30")` +
                        "]"
                ),
                description: "January 2020/November 2020",
            }
        );
    });

    QUnit.test(
        "construct domain based on datetime field (no comparisonOptionId)",
        function (assert) {
            patchDate(2020, 0, 1, 12, 0, 0);
            const referenceMoment = DateTime.local();
            assert.deepEqual(
                constructDateDomain(referenceMoment, "date_field", "datetime", [
                    "this_month",
                    "first_quarter",
                    "this_year",
                ]),
                {
                    domain: new Domain(
                        "[" +
                            `"|", ` +
                            `"&", ("date_field", ">=", "2020-01-01 00:00:00"), ("date_field", "<=", "2020-01-31 23:59:59"), ` +
                            `"&", ("date_field", ">=", "2020-01-01 00:00:00"), ("date_field", "<=", "2020-03-31 23:59:59")` +
                            "]"
                    ),
                    description: "January 2020/Q1 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, "date_field", "datetime", [
                    "second_quarter",
                    "this_year",
                    "last_year",
                ]),
                {
                    domain: new Domain(
                        "[" +
                            `"|", ` +
                            `"&", ("date_field", ">=", "2019-04-01 00:00:00"), ("date_field", "<=", "2019-06-30 23:59:59"), ` +
                            `"&", ("date_field", ">=", "2020-04-01 00:00:00"), ("date_field", "<=", "2020-06-30 23:59:59")` +
                            "]"
                    ),
                    description: "Q2 2019/Q2 2020",
                }
            );
            assert.deepEqual(
                constructDateDomain(referenceMoment, "date_field", "datetime", [
                    "this_year",
                    "this_month",
                    "antepenultimate_month",
                ]),
                {
                    domain: new Domain(
                        "[" +
                            `"|", ` +
                            `"&", ("date_field", ">=", "2020-01-01 00:00:00"), ("date_field", "<=", "2020-01-31 23:59:59"), ` +
                            `"&", ("date_field", ">=", "2020-11-01 00:00:00"), ("date_field", "<=", "2020-11-30 23:59:59")` +
                            "]"
                    ),
                    description: "January 2020/November 2020",
                }
            );
        }
    );

    QUnit.test(
        'construct comparison domain based on date field and option "previous_period"',
        function (assert) {
            patchDate(2020, 0, 1, 12, 0, 0);
            const referenceMoment = DateTime.local();
            assert.deepEqual(
                constructDateDomain(
                    referenceMoment,
                    "date_field",
                    "date",
                    ["this_month", "first_quarter", "this_year"],
                    "previous_period"
                ),
                {
                    domain: new Domain(
                        "[" +
                            `"|",  ` +
                            `"&", ("date_field", ">=", "2019-10-01"), ("date_field", "<=", "2019-10-31"), ` +
                            `"|", ` +
                            `"&", ("date_field", ">=", "2019-11-01"), ("date_field", "<=", "2019-11-30"), ` +
                            `"&", ("date_field", ">=", "2019-12-01"), ("date_field", "<=", "2019-12-31")` +
                            "]"
                    ),
                    description: "October 2019/November 2019/December 2019",
                }
            );
            assert.deepEqual(
                constructDateDomain(
                    referenceMoment,
                    "date_field",
                    "date",
                    ["second_quarter", "this_year", "last_year"],
                    "previous_period"
                ),
                {
                    domain: new Domain(
                        "[" +
                            `"|", ` +
                            `"&", ("date_field", ">=", "2018-01-01"), ("date_field", "<=", "2018-03-31"), ` +
                            `"&", ("date_field", ">=", "2019-01-01"), ("date_field", "<=", "2019-03-31")` +
                            "]"
                    ),
                    description: "Q1 2018/Q1 2019",
                }
            );
            assert.deepEqual(
                constructDateDomain(
                    referenceMoment,
                    "date_field",
                    "date",
                    ["this_year", "antepenultimate_year", "this_month", "antepenultimate_month"],
                    "previous_period"
                ),
                {
                    domain: new Domain(
                        "[" +
                            `"|", ` +
                            `"&", ("date_field", ">=", "2015-02-01"), ("date_field", "<=", "2015-02-28"), ` +
                            `"|", ` +
                            `"&", ("date_field", ">=", "2015-12-01"), ("date_field", "<=", "2015-12-31"), ` +
                            `"|", ` +
                            `"&", ("date_field", ">=", "2017-02-01"), ("date_field", "<=", "2017-02-28"), ` +
                            `"&", ("date_field", ">=", "2017-12-01"), ("date_field", "<=", "2017-12-31")` +
                            "]"
                    ),
                    description: "February 2015/December 2015/February 2017/December 2017",
                }
            );
            assert.deepEqual(
                constructDateDomain(
                    referenceMoment,
                    "date_field",
                    "date",
                    ["this_year", "last_year"],
                    "previous_period"
                ),
                {
                    domain: new Domain(
                        "[" +
                            `"|", ` +
                            `"&", ("date_field", ">=", "2017-01-01"), ("date_field", "<=", "2017-12-31"), ` +
                            `"&", ("date_field", ">=", "2018-01-01"), ("date_field", "<=", "2018-12-31")` +
                            "]"
                    ),
                    description: "2017/2018",
                }
            );
            assert.deepEqual(
                constructDateDomain(
                    referenceMoment,
                    "date_field",
                    "date",
                    ["second_quarter", "third_quarter", "last_year"],
                    "previous_period"
                ),
                {
                    domain: new Domain(
                        "[" +
                            `"|", ` +
                            `"&", ("date_field", ">=", "2018-10-01"), ("date_field", "<=", "2018-12-31"), ` +
                            `"&", ("date_field", ">=", "2019-01-01"), ("date_field", "<=", "2019-03-31")` +
                            "]"
                    ),
                    description: "Q4 2018/Q1 2019",
                }
            );
        }
    );

    QUnit.test(
        'construct comparison domain based on datetime field and option "previous_year"',
        function (assert) {
            patchDate(2020, 5, 1, 13, 0, 0);
            const referenceMoment = DateTime.local();
            assert.deepEqual(
                constructDateDomain(
                    referenceMoment,
                    "date_field",
                    "datetime",
                    ["this_month", "first_quarter", "this_year"],
                    "previous_year"
                ),
                {
                    domain: new Domain(
                        "[" +
                            `"|", ` +
                            `"&", ("date_field", ">=", "2019-06-01 00:00:00"), ("date_field", "<=", "2019-06-30 23:59:59"), ` +
                            `"&", ("date_field", ">=", "2019-01-01 00:00:00"), ("date_field", "<=", "2019-03-31 23:59:59")` +
                            "]"
                    ),
                    description: "June 2019/Q1 2019",
                }
            );
            assert.deepEqual(
                constructDateDomain(
                    referenceMoment,
                    "date_field",
                    "datetime",
                    ["second_quarter", "this_year", "last_year"],
                    "previous_year"
                ),
                {
                    domain: new Domain(
                        "[" +
                            `"|", ` +
                            `"&", ("date_field", ">=", "2018-04-01 00:00:00"), ("date_field", "<=", "2018-06-30 23:59:59"), ` +
                            `"&", ("date_field", ">=", "2019-04-01 00:00:00"), ("date_field", "<=", "2019-06-30 23:59:59")` +
                            "]"
                    ),
                    description: "Q2 2018/Q2 2019",
                }
            );
            assert.deepEqual(
                constructDateDomain(
                    referenceMoment,
                    "date_field",
                    "datetime",
                    ["this_year", "antepenultimate_year", "this_month", "antepenultimate_month"],
                    "previous_year"
                ),
                {
                    domain: new Domain(
                        "[" +
                            `"|", ` +
                            `"&", ("date_field", ">=", "2017-04-01 00:00:00"), ("date_field", "<=", "2017-04-30 23:59:59"), ` +
                            `"|", ` +
                            `"&", ("date_field", ">=", "2017-06-01 00:00:00"), ("date_field", "<=", "2017-06-30 23:59:59"), ` +
                            `"|", ` +
                            `"&", ("date_field", ">=", "2019-04-01 00:00:00"), ("date_field", "<=", "2019-04-30 23:59:59"), ` +
                            `"&", ("date_field", ">=", "2019-06-01 00:00:00"), ("date_field", "<=", "2019-06-30 23:59:59")` +
                            "]"
                    ),
                    description: "April 2017/June 2017/April 2019/June 2019",
                }
            );
        }
    );

    QUnit.test("Quarter option: custom translation", async function (assert) {
        patchDate(2020, 5, 1, 13, 0, 0);
        const referenceMoment = DateTime.local().setLocale("en");
        patchWithCleanup(translatedTerms, { Q2: "Deuxième trimestre de l'an de grâce" });
        assert.deepEqual(
            constructDateDomain(referenceMoment, "date_field", "date", [
                "second_quarter",
                "this_year",
            ]),
            {
                domain: new Domain(
                    `["&", ("date_field", ">=", "2020-04-01"), ("date_field", "<=", "2020-06-30")]`
                ),
                description: "Deuxième trimestre de l'an de grâce 2020",
            },
            "Quarter term should be translated"
        );
    });

    QUnit.test("Quarter option: right to left", async function (assert) {
        patchDate(2020, 5, 1, 13, 0, 0);
        const referenceMoment = DateTime.local().setLocale("en");
        patchWithCleanup(localization, { ...defaultLocalization, direction: "rtl" });
        assert.deepEqual(
            constructDateDomain(referenceMoment, "date_field", "date", [
                "second_quarter",
                "this_year",
            ]),
            {
                domain: new Domain(
                    `["&", ("date_field", ">=", "2020-04-01"), ("date_field", "<=", "2020-06-30")]`
                ),
                description: "2020 Q2",
            },
            "Notation should be right to left"
        );
    });

    QUnit.test("Quarter option: custom translation and right to left", async function (assert) {
        patchDate(2020, 5, 1, 13, 0, 0);
        const referenceMoment = DateTime.local().setLocale("en");
        patchWithCleanup(localization, { ...defaultLocalization, direction: "rtl" });
        patchWithCleanup(translatedTerms, { Q2: "2e Trimestre" });
        assert.deepEqual(
            constructDateDomain(referenceMoment, "date_field", "date", [
                "second_quarter",
                "this_year",
            ]),
            {
                domain: new Domain(
                    `["&", ("date_field", ">=", "2020-04-01"), ("date_field", "<=", "2020-06-30")]`
                ),
                description: "2020 2e Trimestre",
            },
            "Quarter term should be translated and notation should be right to left"
        );
    });
});
