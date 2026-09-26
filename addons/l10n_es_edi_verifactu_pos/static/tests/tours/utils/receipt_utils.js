export function checkVerifactuInvoiceName(number) {
    const steps = [
        {
            content: `verify that Simplified Invoice appears on the receipt`,
            trigger: `.receipt-screen .verifactu-invoice-name:contains('Simplified Invoice')`,
        },
        {
            content: `verify that the invoice number '/${number}' appears on the receipt`,
            trigger: `.receipt-screen .verifactu-invoice-name:contains('/${number}')`,
        },
    ];
    return steps;
}
