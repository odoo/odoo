export function isFrenchCountry(company) {
    return ["FR", "MF", "MQ", "NC", "PF", "RE", "GF", "GP", "TF"].includes(
        company.country_id?.code
    );
}
