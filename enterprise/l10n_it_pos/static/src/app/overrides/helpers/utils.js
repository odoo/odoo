export function isFiscalPrinterConfigured(config) {
    return config.company_id.country_id.code === "IT" && config.it_fiscal_printer_ip;
}

export function isFiscalPrinterActive(config) {
    return isFiscalPrinterConfigured(config) && config.it_fiscal_printer_ip !== "0.0.0.0";
}
