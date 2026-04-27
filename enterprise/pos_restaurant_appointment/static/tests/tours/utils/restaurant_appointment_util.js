export function appointmentLabel(table_num, appointment_name) {
    return [
        {
            content: `Appointment label ${appointment_name}, is present underneath table ${table_num}`,
            trigger: `.floor-map .table:has(.label:contains("${table_num}"):has(.appointment-label:contains("${appointment_name}"))`,
        },
    ];
}
