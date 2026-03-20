import { getBgImageURLFromURL } from "@html_editor/utils/image";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatDateTime } from "@web/views/fields/formatters";

function getEventCoverUrl(coverProperties) {
    coverProperties = JSON.parse(coverProperties);
    return (
        getBgImageURLFromURL(coverProperties["background-image"]) ||
        "/web/static/img/placeholder.png"
    );
}

async function getAddressData(addressId, orm) {
    const addressData = await orm.read(
        "res.partner",
        [addressId],
        ["city", "country_id", "state_id"]
    );

    let countryData;
    if (addressData[0].country_id) {
        countryData = await orm.read(
            "res.country",
            [addressData[0].country_id[0]],
            ["name", "state_required"]
        );
    }

    let stateData;
    if (addressData[0].state_id) {
        stateData = await orm.read("res.country.state", [addressData[0].state_id[0]], ["code"]);
    }

    return {
        address: addressData[0],
        country: countryData && countryData[0],
        state: stateData && stateData[0],
    };
}

export const eventSnapshotSnippetInfo = {
    fields: [
        "display_name",
        "cover_properties",
        "date_begin",
        "date_tz",
        "address_id",
        "event_share_url",
    ],
    get modelDisplayName() {
        return _t("Event");
    },
    getSnippetName: (key) => {
        switch (key) {
            case "columns":
                return "website_mass_mailing_event.s_event_snapshot_columns_fragment";
            case "card":
                return "website_mass_mailing_event.s_event_snapshot_card_fragment";
            case "aside":
                return "website_mass_mailing_event.s_event_snapshot_aside_fragment";
        }
    },
    additionalRenderingContext: async (record, services) => {
        let addressData;
        if (record.address_id) {
            addressData = await getAddressData(record.address_id[0], services.orm);
        }
        return {
            addressData: addressData,
            dateBegin: formatDateTime(deserializeDateTime(record.date_begin), {
                showTime: false,
                format: localization.dateTimeFormat,
                tz: record.date_tz,
            }),
            timeBegin: formatDateTime(deserializeDateTime(record.date_begin), {
                showDate: false,
                format: localization.dateTimeFormat,
                tz: record.date_tz,
            }),
            coverUrl: getEventCoverUrl(record.cover_properties),
        };
    },
};

registry
    .category("mass_mailing.record-snapshot-snippet-info")
    .add("event.event", eventSnapshotSnippetInfo);
