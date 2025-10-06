const { DateTime } = luxon;

/** False if PO is not draft, otherwise loads last toggle state from local storage (defaults to false)  */
export function getSuggestToggleState(poState) {
    if (poState == "draft") {
        const toggle = JSON.parse(localStorage.getItem("purchase_stock.suggest_toggle_state"));
        return toggle ?? { isOn: false };
    }
    return { isOn: false };
}

export function toServerDatetime(datetime) {
    return new Date(datetime).toISOString().slice(0, 19).replace("T", " ");
}

/** Transform a string to its equivalent date range using hardcoded rules */
export function getMonthlyDemandRange(basedOn) {
    const now = DateTime.now();
    let startDate = now;
    let limitDate = now;

    if (!basedOn || basedOn === "actual_demand" || basedOn === "30_days") {
        startDate = now.minus({ days: 30 });
    } else if (basedOn === "one_week") {
        startDate = now.minus({ weeks: 1 });
    } else if (basedOn === "three_months") {
        startDate = now.minus({ months: 3 });
    } else if (basedOn === "one_year") {
        startDate = now.minus({ years: 1 });
    } else {
        startDate = DateTime.local(now.year - 1, now.month, now.day);

        if (basedOn === "last_year_m_plus_1") {
            startDate = startDate.plus({ months: 1 });
        } else if (basedOn === "last_year_m_plus_2") {
            startDate = startDate.plus({ months: 2 });
        }

        if (basedOn === "last_year_quarter") {
            limitDate = startDate.plus({ months: 3 });
        } else {
            limitDate = startDate.plus({ months: 1 });
        }
    }

    return [startDate, limitDate];
}
