/** @odoo-module */
import { getRelativeDateDomain } from "@spreadsheet/global_filters/helpers";
import {
    getDateDomainDurationInDays,
    assertDateDomainEqual,
} from "@spreadsheet/../tests/utils/date_domain";

const { DateTime } = luxon;

QUnit.module("spreadsheet > Global filters helpers", {}, () => {
    QUnit.test("getRelativeDateDomain > last_week (last 7 days)", async function (assert) {
        const now = DateTime.fromISO("2022-05-16");
        const domain = getRelativeDateDomain(now, 0, "last_week", "field", "date");
        assert.equal(getDateDomainDurationInDays(domain), 7);
        assertDateDomainEqual(assert, "field", "2022-05-09", "2022-05-15", domain);
    });

    QUnit.test("getRelativeDateDomain > last_month (last 30 days)", async function (assert) {
        const now = DateTime.fromISO("2022-05-16");
        const domain = getRelativeDateDomain(now, 0, "last_month", "field", "date");
        assert.equal(getDateDomainDurationInDays(domain), 30);
        assertDateDomainEqual(assert, "field", "2022-04-16", "2022-05-15", domain);
    });

    QUnit.test("getRelativeDateDomain > last_year (last 365 days)", async function (assert) {
        const now = DateTime.fromISO("2022-05-16");
        const domain = getRelativeDateDomain(now, 0, "last_year", "field", "date");
        assert.equal(getDateDomainDurationInDays(domain), 365);
        assertDateDomainEqual(assert, "field", "2021-05-16", "2022-05-15", domain);
    });

    QUnit.test(
        "getRelativeDateDomain > last_three_years (last 3 * 365 days)",
        async function (assert) {
            const now = DateTime.fromISO("2022-05-16");
            const domain = getRelativeDateDomain(now, 0, "last_three_years", "field", "date");
            assert.equal(getDateDomainDurationInDays(domain), 3 * 365);
            assertDateDomainEqual(assert, "field", "2019-05-17", "2022-05-15", domain);
        }
    );

    QUnit.test("getRelativeDateDomain > simple date time", async function (assert) {
        const now = DateTime.fromISO("2022-05-16T00:00:00+00:00", { zone: "utc" });
        const domain = getRelativeDateDomain(now, 0, "last_week", "field", "datetime");
        assert.equal(getDateDomainDurationInDays(domain), 7);
        assertDateDomainEqual(
            assert,
            "field",
            "2022-05-09 00:00:00",
            "2022-05-15 23:59:59",
            domain
        );
    });

    QUnit.test("getRelativeDateDomain > date time from middle of day", async function (assert) {
        const now = DateTime.fromISO("2022-05-16T13:59:00+00:00", { zone: "utc" });
        const domain = getRelativeDateDomain(now, 0, "last_week", "field", "datetime");
        assert.equal(getDateDomainDurationInDays(domain), 7);
        assertDateDomainEqual(
            assert,
            "field",
            "2022-05-09 00:00:00",
            "2022-05-15 23:59:59",
            domain
        );
    });

    QUnit.test("getRelativeDateDomain > date time with timezone", async function (assert) {
        const now = DateTime.fromISO("2022-05-16T12:00:00+02:00", { zone: "UTC+2" });
        const domain = getRelativeDateDomain(now, 0, "last_week", "field", "datetime");
        assert.equal(getDateDomainDurationInDays(domain), 7);
        assertDateDomainEqual(
            assert,
            "field",
            "2022-05-08 22:00:00",
            "2022-05-15 21:59:59",
            domain
        );
    });

    QUnit.test(
        "getRelativeDateDomain > date time with timezone on different day than UTC",
        async function (assert) {
            const now = DateTime.fromISO("2022-05-16T01:00:00+02:00", { zone: "UTC+2" });
            const domain = getRelativeDateDomain(now, 0, "last_week", "field", "datetime");
            assert.equal(getDateDomainDurationInDays(domain), 7);
            assertDateDomainEqual(
                assert,
                "field",
                "2022-05-08 22:00:00",
                "2022-05-15 21:59:59",
                domain
            );
        }
    );

    QUnit.test(
        "getRelativeDateDomain > with offset > last_week (last 7 days)",
        async function (assert) {
            const now = DateTime.fromISO("2022-05-16");
            const domain = getRelativeDateDomain(now, -1, "last_week", "field", "date");
            assert.equal(getDateDomainDurationInDays(domain), 7);
            assertDateDomainEqual(assert, "field", "2022-05-02", "2022-05-08", domain);
        }
    );

    QUnit.test("getRelativeDateDomain > with offset (last 30 days)", async function (assert) {
        const now = DateTime.fromISO("2022-05-16");
        const domain = getRelativeDateDomain(now, -2, "last_month", "field", "date");
        assert.equal(getDateDomainDurationInDays(domain), 30);
        assertDateDomainEqual(assert, "field", "2022-02-15", "2022-03-16", domain);
    });

    QUnit.test(
        "getRelativeDateDomain > with offset > last_year (last 365 days)",
        async function (assert) {
            const now = DateTime.fromISO("2022-05-16");
            const domain = getRelativeDateDomain(now, 1, "last_year", "field", "date");
            assert.equal(getDateDomainDurationInDays(domain), 365);
            assertDateDomainEqual(assert, "field", "2022-05-16", "2023-05-15", domain);
        }
    );

    QUnit.test(
        "getRelativeDateDomain > with offset > last_three_years (last 3 * 365 days)",
        async function (assert) {
            const now = DateTime.fromISO("2022-05-16");
            const domain = getRelativeDateDomain(now, -1, "last_three_years", "field", "date");
            assert.equal(getDateDomainDurationInDays(domain), 3 * 365);
            assertDateDomainEqual(assert, "field", "2016-05-17", "2019-05-16", domain);
        }
    );

    QUnit.test("getRelativeDateDomain > with offset > simple date time", async function (assert) {
        const now = DateTime.fromISO("2022-05-16T00:00:00+00:00", { zone: "utc" });
        const domain = getRelativeDateDomain(now, -1, "last_week", "field", "datetime");
        assert.equal(getDateDomainDurationInDays(domain), 7);
        assertDateDomainEqual(
            assert,
            "field",
            "2022-05-02 00:00:00",
            "2022-05-08 23:59:59",
            domain
        );
    });
});
