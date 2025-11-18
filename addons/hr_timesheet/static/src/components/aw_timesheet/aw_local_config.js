const FREQ_KEY = "aw_timesheet_frequency";

export function loadFrequency() {
    return JSON.parse(localStorage.getItem(FREQ_KEY) || "{}");
}

function saveFrequency(freq) {
    localStorage.setItem(FREQ_KEY, JSON.stringify(freq));
}

export function incrementFrequency(title, project_id, task_id, billable) {
    const freq = loadFrequency();
    if (!freq[title]) {
        freq[title] = {};
    }

    const keyObj = {
        project_id: project_id || null,
        task_id: task_id || null,
        billable: !!billable,
    };

    const key = JSON.stringify(keyObj);
    freq[title][key] = (freq[title][key] || 0) + 1;
    saveFrequency(freq);
}
