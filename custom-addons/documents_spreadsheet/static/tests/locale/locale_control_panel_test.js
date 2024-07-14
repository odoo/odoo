/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";

import { createSpreadsheet } from "../spreadsheet_test_utils";

const en_US = {
    name: "English (US)",
    code: "en_US",
    thousandsSeparator: ",",
    decimalSeparator: ".",
    dateFormat: "m/d/yyyy",
    timeFormat: "hh:mm:ss a",
    formulaArgSeparator: ",",
};

const fr_FR = {
    name: "French",
    code: "fr_FR",
    thousandsSeparator: " ",
    decimalSeparator: ",",
    dateFormat: "dd/mm/yyyy",
    timeFormat: "hh:mm:ss",
    formulaArgSeparator: ";",
};

QUnit.module("documents_spreadsheet > Locale Control Panel", {}, function () {
    QUnit.test("No locale icon if user locale matched spreadsheet locale", async function (assert) {
        await createSpreadsheet({
            mockRPC: async function (route, args) {
                if (args.method === "join_spreadsheet_session") {
                    return {
                        name: "Untitled spreadsheet",
                        user_locale: en_US,
                        data: {
                            settings: { locale: en_US },
                        },
                    };
                }
            },
        });
        const icon = document.querySelector(".o_spreadsheet_status .fa-globe");
        assert.notOk(icon);
    });

    QUnit.test("No locale icon if no user locale is given", async function (assert) {
        await createSpreadsheet({
            mockRPC: async function (route, args) {
                if (args.method === "join_spreadsheet_session") {
                    return {
                        name: "Untitled spreadsheet",
                        data: {
                            settings: { locale: en_US },
                        },
                    };
                }
            },
        });
        const icon = document.querySelector(".o_spreadsheet_status .fa-globe");
        assert.notOk(icon);
    });

    QUnit.test(
        "Different locales between user and spreadsheet: display icon as danger",
        async function (assert) {
            await createSpreadsheet({
                mockRPC: async function (route, args) {
                    if (args.method === "join_spreadsheet_session") {
                        return {
                            name: "Untitled spreadsheet",
                            user_locale: fr_FR,
                            data: {
                                settings: { locale: en_US },
                            },
                        };
                    }
                },
            });
            const icon = document.querySelector(".o_spreadsheet_status .fa-globe");
            assert.ok(icon);
            assert.ok(icon.classList.contains("text-danger"));
            assert.equal(
                icon.title,
                "Difference between user locale (fr_FR) and spreadsheet locale (en_US). This spreadsheet is using the formats below:\n" +
                    "- dates: m/d/yyyy\n" +
                    "- numbers: 1,234,567.89"
            );
        }
    );

    QUnit.test("no warning with different locale codes but same formats", async function (assert) {
        await createSpreadsheet({
            mockRPC: async function (route, args) {
                if (args.method === "join_spreadsheet_session") {
                    return {
                        name: "Untitled spreadsheet",
                        user_locale: { ...fr_FR, code: "fr_BE" },
                        data: {
                            settings: { locale: fr_FR },
                        },
                    };
                }
            },
        });
        const icon = document.querySelector(".o_spreadsheet_status .fa-globe");
        assert.notOk(icon);
    });

    QUnit.test("changing spreadsheet locale to user locale: remove icon", async function (assert) {
        const { model } = await createSpreadsheet({
            mockRPC: async function (route, args) {
                if (args.method === "join_spreadsheet_session") {
                    return {
                        name: "Untitled spreadsheet",
                        user_locale: en_US,
                        data: {
                            settings: { locale: fr_FR },
                        },
                    };
                }
            },
        });
        const icon = document.querySelector(".o_spreadsheet_status .fa-globe");
        assert.ok(icon);
        model.dispatch("UPDATE_LOCALE", { locale: en_US });
        await nextTick();
        assert.notOk(document.querySelector(".o_spreadsheet_status .fa-globe"));
    });
});
